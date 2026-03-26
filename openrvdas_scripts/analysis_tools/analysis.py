from pathlib import Path
import numpy as np
import pandas as pd
from .query_tools import timeseries_fetch_tool


def _to_wide(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    data = df.copy()
    data["time"] = pd.to_datetime(data["time"], utc=True, errors="coerce")
    return (
        data.pivot_table(index="time", columns="sensor_label", values="value", aggfunc="mean")
        .sort_index()
    )


def correlation_tool(scalar_path: str | Path, labels: list[str]) -> pd.DataFrame:
    raw = timeseries_fetch_tool(scalar_path, labels)
    wide = _to_wide(raw)
    return wide.corr()


def lag_correlation_tool(
    scalar_path: str | Path,
    x_label: str,
    y_label: str,
    max_lag_steps: int = 120,
) -> tuple[pd.DataFrame, int, float]:
    raw = timeseries_fetch_tool(scalar_path, [x_label, y_label])
    wide = _to_wide(raw).dropna()
    if wide.empty:
        return pd.DataFrame(columns=["lag_steps", "corr"]), 0, float("nan")

    x = wide[x_label]
    y = wide[y_label]
    lags = np.arange(-max_lag_steps, max_lag_steps + 1)
    corr_vals = [x.corr(y.shift(lag)) for lag in lags]
    lag_df = pd.DataFrame({"lag_steps": lags, "corr": corr_vals})
    best_row = lag_df.iloc[lag_df["corr"].abs().idxmax()]
    return lag_df, int(best_row["lag_steps"]), float(best_row["corr"])


def trend_tool(
    scalar_path: str | Path,
    label: str,
    rolling_window: int = 60,
) -> dict:
    raw = timeseries_fetch_tool(scalar_path, [label])
    wide = _to_wide(raw).dropna()
    if wide.empty:
        return {"slope": float("nan"), "intercept": float("nan"), "n": 0}

    s = wide[label]
    x = np.arange(len(s))
    slope, intercept = np.polyfit(x, s.values, 1)
    rolling = s.rolling(rolling_window, min_periods=max(3, rolling_window // 5)).mean()
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "n": int(len(s)),
        "series": s,
        "rolling": rolling,
        "trend_line": intercept + slope * x,
    }


def anomaly_detection_tool(
    scalar_path: str | Path,
    label: str,
    z_threshold: float = 3.0,
) -> pd.DataFrame:
    raw = timeseries_fetch_tool(scalar_path, [label])
    wide = _to_wide(raw).dropna()
    if wide.empty:
        return pd.DataFrame(columns=["time", "value", "zscore"])

    s = wide[label]
    z = (s - s.mean()) / s.std(ddof=0)
    anomalies = pd.DataFrame({"time": s.index, "value": s.values, "zscore": z.values})
    anomalies = anomalies[anomalies["zscore"].abs() >= z_threshold].copy()
    return anomalies.sort_values("zscore", key=lambda col: col.abs(), ascending=False)


def relationship_direction_tool(
    scalar_path: str | Path,
    x_label: str,
    y_label: str,
) -> dict:
    raw = timeseries_fetch_tool(scalar_path, [x_label, y_label])
    wide = _to_wide(raw).dropna()
    if wide.empty:
        return {
            "x_label": x_label,
            "y_label": y_label,
            "n": 0,
            "pearson_r": float("nan"),
            "spearman_r": float("nan"),
            "slope_y_per_x": float("nan"),
            "direction": "unknown",
            "reason": "no overlapping data",
        }

    x = wide[x_label]
    y = wide[y_label]
    slope, _intercept = np.polyfit(x.values, y.values, 1)
    pearson_r = x.corr(y)
    spearman_r = x.rank(method="average").corr(y.rank(method="average"))

    direction = "flat"
    if slope > 0:
        direction = "increase"
    elif slope < 0:
        direction = "decrease"

    return {
        "x_label": x_label,
        "y_label": y_label,
        "n": int(len(wide)),
        "pearson_r": float(pearson_r),
        "spearman_r": float(spearman_r),
        "slope_y_per_x": float(slope),
        "direction": direction,
        "reason": "linear slope sign",
    }


def mean_tool(scalar_path: str | Path, labels: list[str] | str) -> pd.DataFrame:
    """Compute mean values for one or more variables."""
    if isinstance(labels, str):
        labels = [labels]
    raw = timeseries_fetch_tool(scalar_path, labels)
    wide = _to_wide(raw)
    if wide.empty:
        return pd.DataFrame(columns=["sensor_label", "mean"])
    
    result = []
    for col in wide.columns:
        result.append({
            "sensor_label": col,
            "mean": float(wide[col].mean())
        })
    return pd.DataFrame(result)


def median_tool(scalar_path: str | Path, labels: list[str] | str) -> pd.DataFrame:
    """Compute median values for one or more variables."""
    if isinstance(labels, str):
        labels = [labels]
    raw = timeseries_fetch_tool(scalar_path, labels)
    wide = _to_wide(raw)
    if wide.empty:
        return pd.DataFrame(columns=["sensor_label", "median"])
    
    result = []
    for col in wide.columns:
        result.append({
            "sensor_label": col,
            "median": float(wide[col].median())
        })
    return pd.DataFrame(result)


def mode_tool(scalar_path: str | Path, labels: list[str] | str) -> pd.DataFrame:
    """Compute mode values for one or more variables."""
    if isinstance(labels, str):
        labels = [labels]
    raw = timeseries_fetch_tool(scalar_path, labels)
    wide = _to_wide(raw)
    if wide.empty:
        return pd.DataFrame(columns=["sensor_label", "mode", "count"])
    
    result = []
    for col in wide.columns:
        mode_result = wide[col].mode()
        if len(mode_result) > 0:
            mode_val = float(mode_result.iloc[0])
            mode_count = int((wide[col] == mode_val).sum())
        else:
            mode_val = float("nan")
            mode_count = 0
        result.append({
            "sensor_label": col,
            "mode": mode_val,
            "count": mode_count
        })
    return pd.DataFrame(result)


def bounds_tool(scalar_path: str | Path, labels: list[str] | str) -> pd.DataFrame:
    """Compute min/max bounds for one or more variables."""
    if isinstance(labels, str):
        labels = [labels]
    raw = timeseries_fetch_tool(scalar_path, labels)
    wide = _to_wide(raw)
    if wide.empty:
        return pd.DataFrame(columns=["sensor_label", "min_value", "max_value", "range"])
    
    result = []
    for col in wide.columns:
        min_val = float(wide[col].min())
        max_val = float(wide[col].max())
        range_val = max_val - min_val
        result.append({
            "sensor_label": col,
            "min_value": min_val,
            "max_value": max_val,
            "range": range_val
        })
    return pd.DataFrame(result)
