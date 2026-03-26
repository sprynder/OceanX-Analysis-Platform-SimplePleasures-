from pathlib import Path
import duckdb
import pandas as pd


def get_cruise_dir(workspace_root: str | Path, cruise_date: str) -> Path:
    root = Path(workspace_root)
    return root / "data" / f"cruise_{cruise_date.replace('-', '_')}"


def get_default_paths(workspace_root: str | Path, cruise_date: str) -> dict[str, Path]:
    cruise_dir = get_cruise_dir(workspace_root, cruise_date)
    return {
        "cruise_dir": cruise_dir,
        "scalar": cruise_dir / "scalar_timeseries.parquet",
        "geo": cruise_dir / "navigation_track.parquet",
        "geo_speed": cruise_dir / "navigation_geo_speed.parquet",
        "metadata": cruise_dir / "metadata.yaml",
    }


def run_duckdb_query(sql: str) -> pd.DataFrame:
    con = duckdb.connect()
    try:
        return con.execute(sql).df()
    finally:
        con.close()
