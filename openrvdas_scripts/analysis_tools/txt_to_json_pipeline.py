from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any

import numpy as np
import pandas as pd


KEY_VALUE_PATTERN = re.compile(r"([A-Za-z0-9_]+)\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _parse_timestamp_and_payload(line: str) -> tuple[pd.Timestamp | None, str | None]:
    parts = line.strip().split(",", 1)
    if len(parts) != 2:
        return None, None

    ts = pd.to_datetime(parts[0], utc=True, errors="coerce")
    if pd.isna(ts):
        return None, None
    return ts, parts[1].strip()


def _to_minute_series(points: list[tuple[pd.Timestamp, float]]) -> list[list[float]]:
    if not points:
        return []

    frame = pd.DataFrame(points, columns=["time", "value"])
    frame = frame.dropna(subset=["time", "value"]).copy()
    if frame.empty:
        return []

    frame["minute"] = frame["time"].dt.floor("min")
    grouped = frame.groupby("minute", as_index=False)["value"].mean().sort_values("minute")

    output: list[list[float]] = []
    for _, row in grouped.iterrows():
        ts_ms = int(pd.Timestamp(row["minute"]).timestamp() * 1000)
        output.append([ts_ms, float(row["value"])])
    return output


def _to_minute_geo_track(points: list[tuple[pd.Timestamp, float, float, float | None]]) -> dict[str, Any] | None:
    if not points:
        return None

    frame = pd.DataFrame(points, columns=["time", "lon", "lat", "alt"])
    frame = frame.dropna(subset=["time", "lon", "lat"]).copy()
    if frame.empty:
        return None

    frame["minute"] = frame["time"].dt.floor("min")
    grouped = (
        frame.groupby("minute", as_index=False)
        .agg(lon=("lon", "mean"), lat=("lat", "mean"), alt=("alt", "mean"))
        .sort_values("minute")
    )

    coordinates: list[list[float]] = []
    coord_times: list[str] = []
    for _, row in grouped.iterrows():
        lon = float(row["lon"])
        lat = float(row["lat"])
        alt = row["alt"]
        if pd.notna(alt):
            coordinates.append([lon, lat, float(alt)])
        else:
            coordinates.append([lon, lat])
        coord_times.append(pd.Timestamp(row["minute"]).isoformat())

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {"type": "LineString", "coordinates": coordinates},
                "properties": {"coordTimes": coord_times},
            }
        ],
    }


def _parse_nmea_latlon(lat_text: str | None, lat_hemi: str | None, lon_text: str | None, lon_hemi: str | None) -> tuple[float | None, float | None]:
    lat = _safe_float(lat_text)
    lon = _safe_float(lon_text)
    if lat is None or lon is None:
        return None, None

    lat_deg = int(abs(lat) // 100)
    lat_min = abs(lat) - lat_deg * 100
    lat_dec = lat_deg + lat_min / 60.0
    if (lat_hemi or "").upper() == "S":
        lat_dec = -lat_dec

    lon_deg = int(abs(lon) // 100)
    lon_min = abs(lon) - lon_deg * 100
    lon_dec = lon_deg + lon_min / 60.0
    if (lon_hemi or "").upper() == "W":
        lon_dec = -lon_dec

    return lat_dec, lon_dec


@dataclass
class ParsedContent:
    streams: dict[str, list[tuple[pd.Timestamp, float]]]
    units: dict[str, str]
    geo_points: list[tuple[pd.Timestamp, float, float, float | None]]


def _new_parsed_content() -> ParsedContent:
    return ParsedContent(streams={}, units={}, geo_points=[])


def _add_point(parsed: ParsedContent, label: str, unit: str, ts: pd.Timestamp, value: float | None):
    if value is None or pd.isna(value):
        return
    parsed.streams.setdefault(label, []).append((ts, float(value)))
    if label not in parsed.units:
        parsed.units[label] = unit


def _parse_key_value_payload(ts: pd.Timestamp, payload: str, parsed: ParsedContent):
    for key, value_text in KEY_VALUE_PATTERN.findall(payload):
        value = _safe_float(value_text)
        label_map = {
            "t1": ("Internal Temp", "C"),
            "t2": ("External Temp", "C"),
            "c1": ("Conductivity", "S/m"),
            "s": ("Salinity", "PSU"),
        }
        label, unit = label_map.get(key, (key, ""))
        _add_point(parsed, label, unit, ts, value)


def _parse_nmea_payload(ts: pd.Timestamp, payload: str, parsed: ParsedContent):
    sentence = payload.split("*", 1)[0]
    fields = sentence.split(",")
    if not fields:
        return

    sentence_id = fields[0].strip().upper()
    msg_type = sentence_id[-3:] if len(sentence_id) >= 3 else sentence_id

    if msg_type == "GGA":
        lat, lon = _parse_nmea_latlon(
            fields[2] if len(fields) > 2 else None,
            fields[3] if len(fields) > 3 else None,
            fields[4] if len(fields) > 4 else None,
            fields[5] if len(fields) > 5 else None,
        )
        alt = _safe_float(fields[9] if len(fields) > 9 else None)
        if lat is not None and lon is not None:
            parsed.geo_points.append((ts, lon, lat, alt))
        return

    if msg_type == "HDT":
        _add_point(parsed, "Heading", "deg", ts, _safe_float(fields[1] if len(fields) > 1 else None))
        return

    if msg_type == "VTG":
        _add_point(parsed, "COG, True", "deg", ts, _safe_float(fields[1] if len(fields) > 1 else None))
        _add_point(parsed, "COG, Magnetic", "deg", ts, _safe_float(fields[3] if len(fields) > 3 else None))
        _add_point(parsed, "SOG, kts", "kts", ts, _safe_float(fields[5] if len(fields) > 5 else None))
        _add_point(parsed, "SOG, kph", "kph", ts, _safe_float(fields[7] if len(fields) > 7 else None))
        return

    if msg_type == "MWD":
        _add_point(parsed, "Wind Dir, True", "deg", ts, _safe_float(fields[1] if len(fields) > 1 else None))
        _add_point(parsed, "Wind Spd", "m/s", ts, _safe_float(fields[7] if len(fields) > 7 else None))
        return

    if msg_type == "SSB":
        lat, lon = _parse_nmea_latlon(
            fields[8] if len(fields) > 8 else None,
            fields[9] if len(fields) > 9 else None,
            fields[10] if len(fields) > 10 else None,
            fields[11] if len(fields) > 11 else None,
        )
        if lat is not None and lon is not None:
            parsed.geo_points.append((ts, lon, lat, None))

        _add_point(parsed, "HiPAP Depth", "m", ts, _safe_float(fields[12] if len(fields) > 12 else None))
        _add_point(parsed, "HiPAP Range", "m", ts, _safe_float(fields[13] if len(fields) > 13 else None))
        return

    numeric_count = 0
    for idx, raw in enumerate(fields[1:], start=1):
        value = _safe_float(raw)
        if value is not None:
            _add_point(parsed, f"Field {idx}", "", ts, value)
            numeric_count += 1
    if numeric_count == 0:
        return


def convert_openrvdas_txt_to_json(
    txt_path: str | Path,
    json_path: str | Path | None = None,
) -> dict[str, Any]:
    txt_file = Path(txt_path)
    out_file = Path(json_path) if json_path else txt_file.with_suffix(".json")

    parsed = _new_parsed_content()

    with txt_file.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            ts, payload = _parse_timestamp_and_payload(line)
            if ts is None or payload is None:
                continue

            if "=" in payload and payload.startswith(("t", "c", "s", "T", "C", "S")):
                _parse_key_value_payload(ts, payload, parsed)
            elif payload.startswith("$"):
                _parse_nmea_payload(ts, payload, parsed)
            else:
                _parse_key_value_payload(ts, payload, parsed)

    visualizer_data: list[dict[str, Any]] = []

    if parsed.geo_points:
        geo_obj = _to_minute_geo_track(parsed.geo_points)
        if geo_obj is not None:
            visualizer_data.append(geo_obj)

    for label, points in parsed.streams.items():
        data = _to_minute_series(points)
        if not data:
            continue
        visualizer_data.append(
            {
                "data": data,
                "unit": parsed.units.get(label, ""),
                "label": label,
            }
        )

    payload = {"visualizerData": visualizer_data}
    out_file.write_text(json.dumps(payload, indent=4), encoding="utf-8")

    return {
        "txt_path": txt_file.as_posix(),
        "json_path": out_file.as_posix(),
        "streams": len(visualizer_data),
        "geo_track": bool(parsed.geo_points),
    }


def convert_missing_openrvdas_json(
    openrvdas_root: str | Path,
    overwrite: bool = False,
) -> pd.DataFrame:
    root = Path(openrvdas_root)
    txt_files = sorted(root.rglob("*.txt"))

    rows: list[dict[str, Any]] = []
    for txt_file in txt_files:
        json_file = txt_file.with_suffix(".json")
        if json_file.exists() and not overwrite:
            rows.append(
                {
                    "txt_file": txt_file.as_posix(),
                    "json_file": json_file.as_posix(),
                    "status": "skipped_exists",
                    "streams": np.nan,
                }
            )
            continue

        try:
            result = convert_openrvdas_txt_to_json(txt_file, json_file)
            rows.append(
                {
                    "txt_file": result["txt_path"],
                    "json_file": result["json_path"],
                    "status": "converted",
                    "streams": result["streams"],
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "txt_file": txt_file.as_posix(),
                    "json_file": json_file.as_posix(),
                    "status": f"error: {exc}",
                    "streams": np.nan,
                }
            )

    return pd.DataFrame(rows)
