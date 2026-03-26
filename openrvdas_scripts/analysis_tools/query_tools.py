from pathlib import Path
import pandas as pd
from .common import run_duckdb_query


def list_variables_tool(scalar_path: str | Path) -> pd.DataFrame:
    scalar = Path(scalar_path).as_posix()
    sql = f"""
    SELECT
      sensor_label,
      ANY_VALUE(unit) AS unit,
      COUNT(*) AS n,
      MIN(time) AS t_min,
      MAX(time) AS t_max
    FROM read_parquet('{scalar}')
    GROUP BY sensor_label
    ORDER BY sensor_label
    """
    return run_duckdb_query(sql)


def timeseries_fetch_tool(
    scalar_path: str | Path,
    labels: list[str],
    start_time: str | None = None,
    end_time: str | None = None,
) -> pd.DataFrame:
    if not labels:
        return pd.DataFrame(columns=["time", "sensor_label", "value", "unit", "source_file"])
    scalar = Path(scalar_path).as_posix()
    labels_sql = ", ".join(["'" + lbl.replace("'", "''") + "'" for lbl in labels])
    where_parts = [f"sensor_label IN ({labels_sql})"]
    if start_time:
        where_parts.append(f"time >= '{pd.Timestamp(start_time).isoformat()}'")
    if end_time:
        where_parts.append(f"time <= '{pd.Timestamp(end_time).isoformat()}'")
    where_sql = " AND ".join(where_parts)
    sql = f"""
    SELECT time, sensor_label, value, unit, source_file
    FROM read_parquet('{scalar}')
    WHERE {where_sql}
    ORDER BY time, sensor_label
    """
    return run_duckdb_query(sql)


def where_was_extreme_tool(
    scalar_path: str | Path,
    geo_path: str | Path,
    variable: str,
    mode: str = "max",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if mode not in {"max", "min"}:
        raise ValueError("mode must be 'max' or 'min'")
    scalar = Path(scalar_path).as_posix()
    geo = Path(geo_path).as_posix()
    order = "DESC" if mode == "max" else "ASC"

    per_track_sql = f"""
    WITH extreme AS (
      SELECT time, value, sensor_label
      FROM read_parquet('{scalar}')
      WHERE sensor_label = '{variable.replace("'", "''")}'
      ORDER BY value {order}, time ASC
      LIMIT 1
    )
    SELECT
      e.time,
      e.sensor_label,
      e.value,
      g.source_file AS nav_source_file,
      g.longitude,
      g.latitude
    FROM extreme e
    JOIN read_parquet('{geo}') g
      ON g.time = e.time
    ORDER BY nav_source_file
    """

    mean_pos_sql = f"""
    WITH extreme AS (
      SELECT time, value, sensor_label
      FROM read_parquet('{scalar}')
      WHERE sensor_label = '{variable.replace("'", "''")}'
      ORDER BY value {order}, time ASC
      LIMIT 1
    )
    SELECT
      e.time,
      e.sensor_label,
      e.value,
      AVG(g.longitude) AS mean_longitude,
      AVG(g.latitude) AS mean_latitude,
      COUNT(*) AS matched_nav_points
    FROM extreme e
    JOIN read_parquet('{geo}') g
      ON g.time = e.time
    GROUP BY e.time, e.sensor_label, e.value
    """

    return run_duckdb_query(per_track_sql), run_duckdb_query(mean_pos_sql)


def summary_stats_tool(scalar_path: str | Path, labels: list[str] | None = None) -> pd.DataFrame:
    scalar = Path(scalar_path).as_posix()
    where_sql = ""
    if labels:
        labels_sql = ", ".join(["'" + lbl.replace("'", "''") + "'" for lbl in labels])
        where_sql = f"WHERE sensor_label IN ({labels_sql})"

    sql = f"""
    SELECT
      sensor_label,
      ANY_VALUE(unit) AS unit,
      COUNT(*) AS n,
      ROUND(AVG(value), 5) AS mean,
      ROUND(STDDEV_POP(value), 5) AS std,
      MIN(value) AS v_min,
      MAX(value) AS v_max,
      MIN(time) AS t_min,
      MAX(time) AS t_max
    FROM read_parquet('{scalar}')
    {where_sql}
    GROUP BY sensor_label
    ORDER BY sensor_label
    """
    return run_duckdb_query(sql)
