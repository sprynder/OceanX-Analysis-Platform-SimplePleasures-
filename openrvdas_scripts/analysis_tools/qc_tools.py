from pathlib import Path
import pandas as pd
from .common import run_duckdb_query


def timestamp_alignment_tool(scalar_path: str | Path, geo_path: str | Path, variable: str | None = None) -> dict:
    scalar = Path(scalar_path).as_posix()
    geo = Path(geo_path).as_posix()
    where_sql = ""
    if variable:
        where_sql = f"WHERE sensor_label = '{variable.replace("'", "''")}'"

    scalar_times = run_duckdb_query(
        f"SELECT DISTINCT time FROM read_parquet('{scalar}') {where_sql}"
    )["time"]
    geo_times = run_duckdb_query(f"SELECT DISTINCT time FROM read_parquet('{geo}')")["time"]

    s = pd.Index(pd.to_datetime(scalar_times, utc=True, errors="coerce").dropna().unique())
    g = pd.Index(pd.to_datetime(geo_times, utc=True, errors="coerce").dropna().unique())
    overlap = s.intersection(g)
    return {
        "scalar_unique_times": int(len(s)),
        "geo_unique_times": int(len(g)),
        "overlap": int(len(overlap)),
        "scalar_covered_by_geo": float(len(overlap) / len(s)) if len(s) else float("nan"),
        "geo_covered_by_scalar": float(len(overlap) / len(g)) if len(g) else float("nan"),
    }


def data_gaps_tool(
    scalar_path: str | Path,
    variable: str,
    expected_step_seconds: int = 60,
) -> pd.DataFrame:
    scalar = Path(scalar_path).as_posix()
    sql = f"""
    SELECT time
    FROM read_parquet('{scalar}')
    WHERE sensor_label = '{variable.replace("'", "''")}'
    ORDER BY time
    """
    df = run_duckdb_query(sql)
    if df.empty:
        return pd.DataFrame(columns=["gap_start", "gap_end", "gap_seconds"])
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    df = df.dropna().sort_values("time").reset_index(drop=True)
    df["prev_time"] = df["time"].shift(1)
    df["gap_seconds"] = (df["time"] - df["prev_time"]).dt.total_seconds()
    gaps = df[df["gap_seconds"] > expected_step_seconds].copy()
    gaps = gaps.rename(columns={"prev_time": "gap_start", "time": "gap_end"})
    return gaps[["gap_start", "gap_end", "gap_seconds"]]


def sensor_qc_tool(
    scalar_path: str | Path,
    variable: str,
    min_valid: float | None = None,
    max_valid: float | None = None,
) -> pd.DataFrame:
    scalar = Path(scalar_path).as_posix()
    sql = f"""
    SELECT time, sensor_label, value, unit, source_file
    FROM read_parquet('{scalar}')
    WHERE sensor_label = '{variable.replace("'", "''")}'
    ORDER BY time
    """
    df = run_duckdb_query(sql)
    if df.empty:
        return df
    mask = pd.Series([False] * len(df))
    if min_valid is not None:
        mask |= df["value"] < min_valid
    if max_valid is not None:
        mask |= df["value"] > max_valid
    return df[mask].reset_index(drop=True)
