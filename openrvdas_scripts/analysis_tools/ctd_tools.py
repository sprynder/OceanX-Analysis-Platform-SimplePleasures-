from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .query_tools import list_variables_tool, timeseries_fetch_tool


CTD_LABEL_CANDIDATES: dict[str, list[str]] = {
    "temperature": ["Temperature", "External Temp", "Temp", "Water Temperature"],
    "salinity": ["Salinity", "Practical Salinity"],
    "depth": ["Depth", "CTD Depth", "Depth (m)", "Sea Depth"],
    "pressure": ["Pressure", "CTD Pressure", "Press", "Pressure (dbar)"],
    "conductivity": ["Conductivity", "Cond", "CTD Conductivity"],
    "oxygen": ["Oxygen", "Dissolved Oxygen", "DO", "O2"],
}


def _resolve_label(available_labels: list[str], candidates: list[str]) -> str | None:
    available_lower = {label.lower(): label for label in available_labels}

    for candidate in candidates:
        match = available_lower.get(candidate.lower())
        if match:
            return match

    for candidate in candidates:
        candidate_lower = candidate.lower()
        for label in available_labels:
            if candidate_lower in label.lower():
                return label

    return None


def ctd_detect_variable_labels_tool(scalar_path: str | Path) -> pd.DataFrame:
    variables_df = list_variables_tool(scalar_path)
    if variables_df.empty:
        return pd.DataFrame(columns=["variable", "selected_label", "status"])

    available_labels = variables_df["sensor_label"].dropna().astype(str).tolist()
    rows: list[dict[str, Any]] = []
    for variable, candidates in CTD_LABEL_CANDIDATES.items():
        selected = _resolve_label(available_labels, candidates)
        rows.append(
            {
                "variable": variable,
                "selected_label": selected,
                "status": "found" if selected else "missing",
            }
        )

    return pd.DataFrame(rows)


def ctd_prepare_dataframe_tool(
    scalar_path: str | Path,
    start_time: str | None = None,
    end_time: str | None = None,
    require_core: bool = False,
) -> pd.DataFrame:
    label_map_df = ctd_detect_variable_labels_tool(scalar_path)
    selected_map = {
        row["variable"]: row["selected_label"]
        for _, row in label_map_df.iterrows()
        if pd.notna(row["selected_label"])
    }

    labels_to_fetch = [label for label in selected_map.values() if isinstance(label, str)]
    if not labels_to_fetch:
        return pd.DataFrame(columns=["time", "temperature", "salinity", "depth", "pressure", "conductivity", "oxygen"])

    raw_df = timeseries_fetch_tool(
        scalar_path,
        labels=labels_to_fetch,
        start_time=start_time,
        end_time=end_time,
    )
    if raw_df.empty:
        return pd.DataFrame(columns=["time", "temperature", "salinity", "depth", "pressure", "conductivity", "oxygen"])

    raw_df = raw_df.copy()
    raw_df["time"] = pd.to_datetime(raw_df["time"], utc=True, errors="coerce")
    wide_df = (
        raw_df.pivot_table(index="time", columns="sensor_label", values="value", aggfunc="mean")
        .sort_index()
        .reset_index()
    )

    rename_map = {
        selected_map[key]: key
        for key in ["temperature", "salinity", "depth", "pressure", "conductivity", "oxygen"]
        if key in selected_map
    }
    ctd_df = wide_df.rename(columns=rename_map)

    for expected_column in ["temperature", "salinity", "depth", "pressure", "conductivity", "oxygen"]:
        if expected_column not in ctd_df.columns:
            ctd_df[expected_column] = np.nan

    if ctd_df["depth"].isna().all() and not ctd_df["pressure"].isna().all():
        ctd_df["depth"] = ctd_df["pressure"]

    ordered_columns = ["time", "temperature", "salinity", "depth", "pressure", "conductivity", "oxygen"]
    ctd_df = ctd_df[ordered_columns].sort_values("time").reset_index(drop=True)

    if require_core:
        ctd_df = ctd_df.dropna(subset=["temperature", "salinity", "depth"]).reset_index(drop=True)

    return ctd_df


def ctd_profile_segments_tool(
    ctd_df: pd.DataFrame,
    min_points: int = 20,
    min_depth_change: float = 2.0,
    max_gap_seconds: float = 300.0,
) -> pd.DataFrame:
    if ctd_df.empty or "time" not in ctd_df.columns or "depth" not in ctd_df.columns:
        return pd.DataFrame(
            columns=[
                "segment_id",
                "phase",
                "n",
                "start_time",
                "end_time",
                "depth_start",
                "depth_end",
                "depth_min",
                "depth_max",
                "depth_change",
            ]
        )

    work_df = ctd_df[["time", "depth"]].copy()
    work_df["time"] = pd.to_datetime(work_df["time"], utc=True, errors="coerce")
    work_df["depth"] = pd.to_numeric(work_df["depth"], errors="coerce")
    work_df = work_df.dropna(subset=["time", "depth"]).sort_values("time").reset_index(drop=True)
    if work_df.empty:
        return pd.DataFrame()

    work_df["dt_seconds"] = work_df["time"].diff().dt.total_seconds().fillna(0)
    work_df["dz"] = work_df["depth"].diff().fillna(0)
    work_df["direction"] = np.sign(work_df["dz"])
    work_df["direction"] = work_df["direction"].replace(0, np.nan).ffill().fillna(0)

    direction_change = work_df["direction"].ne(work_df["direction"].shift(1)).fillna(True)
    large_gap = work_df["dt_seconds"] > max_gap_seconds
    work_df["segment_id"] = (direction_change | large_gap).cumsum()

    summary_df = (
        work_df.groupby("segment_id", as_index=False)
        .agg(
            n=("depth", "size"),
            start_time=("time", "min"),
            end_time=("time", "max"),
            depth_start=("depth", "first"),
            depth_end=("depth", "last"),
            depth_min=("depth", "min"),
            depth_max=("depth", "max"),
        )
    )
    summary_df["depth_change"] = (summary_df["depth_end"] - summary_df["depth_start"]).abs()
    summary_df["phase"] = np.where(summary_df["depth_end"] >= summary_df["depth_start"], "downcast", "upcast")

    summary_df = summary_df[
        (summary_df["n"] >= min_points) & (summary_df["depth_change"] >= min_depth_change)
    ].reset_index(drop=True)

    return summary_df[
        [
            "segment_id",
            "phase",
            "n",
            "start_time",
            "end_time",
            "depth_start",
            "depth_end",
            "depth_min",
            "depth_max",
            "depth_change",
        ]
    ]


def ctd_profile_summary_tool(ctd_df: pd.DataFrame, depth_bin_m: float = 5.0) -> pd.DataFrame:
    if ctd_df.empty or "depth" not in ctd_df.columns:
        return pd.DataFrame(columns=["depth_bin_m", "n", "temp_mean", "sal_mean", "cond_mean", "oxy_mean"])

    work_df = ctd_df.copy()
    work_df["depth"] = pd.to_numeric(work_df["depth"], errors="coerce")
    work_df = work_df.dropna(subset=["depth"]).copy()
    if work_df.empty:
        return pd.DataFrame(columns=["depth_bin_m", "n", "temp_mean", "sal_mean", "cond_mean", "oxy_mean"])

    work_df["depth_bin_m"] = np.floor(work_df["depth"] / depth_bin_m) * depth_bin_m

    summary_df = (
        work_df.groupby("depth_bin_m", as_index=False)
        .agg(
            n=("depth", "size"),
            temp_mean=("temperature", "mean"),
            sal_mean=("salinity", "mean"),
            cond_mean=("conductivity", "mean"),
            oxy_mean=("oxygen", "mean"),
        )
        .sort_values("depth_bin_m")
        .reset_index(drop=True)
    )

    return summary_df


def mixed_layer_depth_tool(
    ctd_df: pd.DataFrame,
    temp_threshold_c: float = 0.2,
    reference_window_m: float = 5.0,
) -> dict[str, Any]:
    if ctd_df.empty:
        return {"mld_depth_m": np.nan, "reason": "empty_dataframe"}

    work_df = ctd_df[["depth", "temperature"]].copy()
    work_df["depth"] = pd.to_numeric(work_df["depth"], errors="coerce")
    work_df["temperature"] = pd.to_numeric(work_df["temperature"], errors="coerce")
    work_df = work_df.dropna(subset=["depth", "temperature"]).sort_values("depth")
    if work_df.empty:
        return {"mld_depth_m": np.nan, "reason": "missing_depth_or_temperature"}

    surface_depth = float(work_df["depth"].min())
    surface_mask = work_df["depth"] <= (surface_depth + reference_window_m)
    if not surface_mask.any():
        return {"mld_depth_m": np.nan, "reason": "no_surface_reference"}

    surface_temp = float(work_df.loc[surface_mask, "temperature"].mean())
    threshold_temp = surface_temp - temp_threshold_c

    below_threshold = work_df[work_df["temperature"] <= threshold_temp]
    if below_threshold.empty:
        return {
            "mld_depth_m": np.nan,
            "surface_temp_c": surface_temp,
            "threshold_temp_c": threshold_temp,
            "reason": "threshold_not_reached",
        }

    mld_depth = float(below_threshold.iloc[0]["depth"])
    return {
        "mld_depth_m": mld_depth,
        "surface_temp_c": surface_temp,
        "threshold_temp_c": threshold_temp,
        "reason": "ok",
    }


def thermocline_depth_tool(ctd_df: pd.DataFrame) -> dict[str, Any]:
    if ctd_df.empty:
        return {"thermocline_depth_m": np.nan, "dtemp_dz": np.nan, "reason": "empty_dataframe"}

    work_df = ctd_df[["depth", "temperature"]].copy()
    work_df["depth"] = pd.to_numeric(work_df["depth"], errors="coerce")
    work_df["temperature"] = pd.to_numeric(work_df["temperature"], errors="coerce")
    work_df = work_df.dropna(subset=["depth", "temperature"]).sort_values("depth")
    if len(work_df) < 3:
        return {"thermocline_depth_m": np.nan, "dtemp_dz": np.nan, "reason": "insufficient_points"}

    collapsed_df = work_df.groupby("depth", as_index=False)["temperature"].mean().sort_values("depth")
    if len(collapsed_df) < 3:
        return {"thermocline_depth_m": np.nan, "dtemp_dz": np.nan, "reason": "insufficient_unique_depths"}

    depth_values = collapsed_df["depth"].to_numpy(dtype=float)
    temp_values = collapsed_df["temperature"].to_numpy(dtype=float)
    gradient_values = np.gradient(temp_values, depth_values)

    index_min_gradient = int(np.argmin(gradient_values))
    return {
        "thermocline_depth_m": float(depth_values[index_min_gradient]),
        "dtemp_dz": float(gradient_values[index_min_gradient]),
        "reason": "ok",
    }


def ctd_qc_tool(
    ctd_df: pd.DataFrame,
    temperature_range: tuple[float, float] = (-2.5, 40.0),
    salinity_range: tuple[float, float] = (0.0, 42.0),
    depth_range: tuple[float, float] = (0.0, 11000.0),
    spike_z_threshold: float = 4.0,
) -> pd.DataFrame:
    if ctd_df.empty:
        return pd.DataFrame()

    qc_df = ctd_df.copy()
    for field in ["temperature", "salinity", "depth"]:
        qc_df[field] = pd.to_numeric(qc_df.get(field), errors="coerce")

    qc_df["flag_temp_range"] = qc_df["temperature"].notna() & (~qc_df["temperature"].between(temperature_range[0], temperature_range[1]))
    qc_df["flag_sal_range"] = qc_df["salinity"].notna() & (~qc_df["salinity"].between(salinity_range[0], salinity_range[1]))
    qc_df["flag_depth_range"] = qc_df["depth"].notna() & (~qc_df["depth"].between(depth_range[0], depth_range[1]))

    temp_delta = qc_df["temperature"].diff()
    sal_delta = qc_df["salinity"].diff()

    temp_spike_scale = temp_delta.std(ddof=0)
    sal_spike_scale = sal_delta.std(ddof=0)

    if pd.notna(temp_spike_scale) and temp_spike_scale > 0:
        qc_df["flag_temp_spike"] = (temp_delta.abs() / temp_spike_scale) > spike_z_threshold
    else:
        qc_df["flag_temp_spike"] = False

    if pd.notna(sal_spike_scale) and sal_spike_scale > 0:
        qc_df["flag_sal_spike"] = (sal_delta.abs() / sal_spike_scale) > spike_z_threshold
    else:
        qc_df["flag_sal_spike"] = False

    qc_df["flag_any"] = qc_df[
        [
            "flag_temp_range",
            "flag_sal_range",
            "flag_depth_range",
            "flag_temp_spike",
            "flag_sal_spike",
        ]
    ].any(axis=1)

    return qc_df.loc[qc_df["flag_any"]].reset_index(drop=True)
