from pathlib import Path
import numpy as np
import pandas as pd
from .common import run_duckdb_query


R_EARTH_M = 6371000.0
MPS_TO_KNOTS = 1.9438444924406


def _haversine_m(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = np.radians([lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R_EARTH_M * c


def track_extract_tool(
    geo_path: str | Path,
    start_time: str | None = None,
    end_time: str | None = None,
) -> pd.DataFrame:
    geo = Path(geo_path).as_posix()
    where_parts = ["1=1"]
    if start_time:
        where_parts.append(f"time >= '{pd.Timestamp(start_time).isoformat()}'")
    if end_time:
        where_parts.append(f"time <= '{pd.Timestamp(end_time).isoformat()}'")
    where_sql = " AND ".join(where_parts)
    sql = f"""
    SELECT source_file, time, longitude, latitude, altitude
    FROM read_parquet('{geo}')
    WHERE {where_sql}
    ORDER BY time, source_file
    """
    return run_duckdb_query(sql)


def geo_join_tool(
    scalar_path: str | Path,
    geo_path: str | Path,
    variable: str,
) -> pd.DataFrame:
    scalar = Path(scalar_path).as_posix()
    geo = Path(geo_path).as_posix()
    sql = f"""
    SELECT
      s.time,
      s.sensor_label,
      s.value,
      s.source_file AS scalar_source_file,
      g.source_file AS geo_source_file,
      g.longitude,
      g.latitude
    FROM read_parquet('{scalar}') s
    JOIN read_parquet('{geo}') g
      ON s.time = g.time
    WHERE s.sensor_label = '{variable.replace("'", "''")}'
    ORDER BY s.time, g.source_file
    """
    return run_duckdb_query(sql)


def distance_speed_tool(geo_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    track = track_extract_tool(geo_path)
    if track.empty:
        return pd.DataFrame(), pd.DataFrame()

    track["time"] = pd.to_datetime(track["time"], utc=True, errors="coerce")
    parts = []
    for source_file, group in track.groupby("source_file", sort=True):
        g = group.sort_values("time").copy()
        g["lon_prev"] = g["longitude"].shift(1)
        g["lat_prev"] = g["latitude"].shift(1)
        g["time_prev"] = g["time"].shift(1)
        dt_s = (g["time"] - g["time_prev"]).dt.total_seconds()
        dist_m = _haversine_m(
            g["lon_prev"].fillna(g["longitude"]),
            g["lat_prev"].fillna(g["latitude"]),
            g["longitude"],
            g["latitude"],
        )
        g["distance_m"] = np.where(dt_s > 0, dist_m, np.nan)
        g["dt_s"] = np.where(dt_s > 0, dt_s, np.nan)
        g["speed_mps"] = g["distance_m"] / g["dt_s"]
        g["speed_knots"] = g["speed_mps"] * MPS_TO_KNOTS
        parts.append(g)

    speed_df = pd.concat(parts, ignore_index=True)
    summary = (
        speed_df.groupby("source_file", dropna=False)["speed_knots"]
        .agg(["count", "mean", "median", "max"])
        .rename(columns={"count": "n"})
        .reset_index()
    )
    return speed_df, summary
