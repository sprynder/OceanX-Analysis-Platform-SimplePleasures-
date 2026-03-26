from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from .query_tools import timeseries_fetch_tool, summary_stats_tool
from .geo_tools import track_extract_tool


def plot_timeseries_tool(
    scalar_path: str | Path,
    labels: list[str],
    start_time: str | None = None,
    end_time: str | None = None,
):
    df = timeseries_fetch_tool(scalar_path, labels, start_time=start_time, end_time=end_time)
    if df.empty:
        return None
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    fig, ax = plt.subplots(figsize=(10, 4))
    for label, g in df.groupby("sensor_label"):
        ax.plot(g["time"], g["value"], label=label)
    ax.set_title("Timeseries")
    ax.set_xlabel("Time")
    ax.set_ylabel("Value")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def plot_map_tool(geo_path: str | Path):
    geo = track_extract_tool(geo_path)
    if geo.empty:
        return None
    fig, ax = plt.subplots(figsize=(7, 6))
    for source_file, g in geo.groupby("source_file"):
        ax.plot(g["longitude"], g["latitude"], label=Path(source_file).name)
    ax.set_title("Track Map")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    return fig


def analysis_report_tool(scalar_path: str | Path, labels: list[str] | None = None) -> dict:
    stats = summary_stats_tool(scalar_path, labels=labels)
    report = {
        "n_variables": int(stats["sensor_label"].nunique()) if not stats.empty else 0,
        "total_rows": int(stats["n"].sum()) if not stats.empty else 0,
        "stats": stats,
    }
    return report
