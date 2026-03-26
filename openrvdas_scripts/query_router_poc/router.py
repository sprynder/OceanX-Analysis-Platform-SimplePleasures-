from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
import re
from typing import Any, TypedDict

import numpy as np
import pandas as pd

from analysis_tools.analysis import anomaly_detection_tool, correlation_tool, lag_correlation_tool, relationship_direction_tool, trend_tool, mean_tool, median_tool, mode_tool, bounds_tool
from analysis_tools.ctd_tools import ctd_prepare_dataframe_tool, ctd_profile_summary_tool, mixed_layer_depth_tool, thermocline_depth_tool
from analysis_tools.geo_tools import distance_speed_tool, geo_join_tool
from analysis_tools.qc_tools import data_gaps_tool, sensor_qc_tool, timestamp_alignment_tool
from analysis_tools.query_tools import list_variables_tool, summary_stats_tool, timeseries_fetch_tool, where_was_extreme_tool


class RouterState(TypedDict, total=False):
    question: str
    scalar_path: str
    geo_path: str
    intent: str
    entities: dict[str, Any]
    result: dict[str, Any]
    error: str


@dataclass
class RouterResult:
    intent: str
    entities: dict[str, Any]
    answer_text: str
    table: pd.DataFrame | None


DEFAULT_LABEL_ALIASES = {
    "salinity": "Salinity",
    "wind speed": "Wind Spd",
    "wind spd": "Wind Spd",
    "chlorophyll": "Chlorophyll Signal",
    "temperature": "Temperature",
    "external temp": "External Temp",
}

INTENT_TEMPLATES = {
    "when_max": [
        "when was salinity the highest",
        "when did wind speed reach max",
        "time of maximum chlorophyll",
        "what time did salinity peak",
    ],
    "where_max": [
        "where was salinity the highest",
        "in what location was salinity highest",
        "location of maximum chlorophyll",
    ],
    "when_min": [
        "when was wind speed the lowest",
        "time of minimum salinity",
        "when did chlorophyll reach minimum",
    ],
    "where_min": [
        "where was salinity the lowest",
        "location of minimum wind speed",
        "in what location was chlorophyll lowest",
        "location of minimum salinity",
    ],
    "correlation": [
        "correlation between wind speed and salinity",
        "how are salinity and temperature related",
        "relationship between chlorophyll and wind speed",
    ],
    "relationship_direction": [
        "does salinity decrease with temperature",
        "does wind speed increase with salinity",
        "is salinity increasing as temperature rises",
    ],
    "list_variables": [
        "list all variables",
        "what variables are available",
    ],
    "summary_stats": [
        "summary statistics for salinity",
        "mean and standard deviation by variable",
    ],
    "timeseries_fetch": [
        "show time series for salinity",
        "fetch wind speed timeseries",
    ],
    "lag_correlation": [
        "lag correlation between wind speed and salinity",
        "best lag for salinity and temperature",
    ],
    "trend": [
        "trend of salinity",
        "slope for wind speed over time",
    ],
    "anomaly_detection": [
        "detect anomalies in salinity",
        "find outliers in wind speed",
    ],
    "timestamp_alignment": [
        "timestamp alignment between scalar and navigation",
        "how aligned are salinity timestamps with geo",
    ],
    "data_gaps": [
        "find data gaps in salinity",
        "missing intervals for wind speed",
    ],
    "sensor_qc": [
        "qc check salinity",
        "quality control for wind speed",
    ],
    "speed_summary": [
        "speed summary by navigation source",
        "distance and speed stats from track",
    ],
    "geo_join": [
        "join salinity with geospatial track",
        "show salinity with longitude and latitude",
    ],
    "ctd_profile_summary": [
        "ctd depth profile summary",
        "depth-binned ctd summary",
    ],
    "ctd_mld": [
        "mixed layer depth",
        "compute mld from ctd",
    ],
    "ctd_thermocline": [
        "thermocline depth",
        "estimate thermocline from ctd",
    ],
    "mean": [
        "mean of salinity",
        "average wind speed",
        "mean value of temperature",
        "what is the mean salinity",
    ],
    "median": [
        "median of salinity",
        "median wind speed",
        "middle value of temperature",
        "what is the median salinity",
    ],
    "mode": [
        "mode of salinity",
        "most frequent wind speed",
        "modal value of temperature",
        "what is the mode salinity",
    ],
    "bounds": [
        "bounds of salinity",
        "min and max wind speed",
        "range of temperature",
        "minimum and maximum salinity",
        "bounds for salinity data",
    ],
}

SEMANTIC_SYNONYMS = {
    "location": "where",
    "position": "where",
    "place": "where",
    "highest": "max",
    "maximum": "max",
    "peak": "max",
    "lowest": "min",
    "minimum": "min",
    "relation": "correlation",
    "related": "correlation",
    "relationship": "correlation",
    "variables": "variable",
    "timeseries": "time series",
    "timeseries": "time series",
    "outliers": "anomaly",
    "aligned": "alignment",
}

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_SCORE_THRESHOLD = 0.35
JACCARD_SCORE_THRESHOLD = 0.3

_EMBEDDER: Any | None = None
_EMBEDDING_TEMPLATE_MAT: np.ndarray | None = None
_EMBEDDING_TEMPLATE_INTENTS: list[str] = []
_EMBEDDING_INIT_ERROR: str | None = None


def _normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _tokenize(text: str) -> set[str]:
    normalized = _normalize_question(text)
    tokens = re.findall(r"[a-z0-9_]+", normalized)
    expanded: list[str] = []
    for token in tokens:
        expanded.append(SEMANTIC_SYNONYMS.get(token, token))
    return set(expanded)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a.intersection(b)) / len(a.union(b))


def _init_embedding_matcher() -> None:
    global _EMBEDDER, _EMBEDDING_TEMPLATE_MAT, _EMBEDDING_TEMPLATE_INTENTS, _EMBEDDING_INIT_ERROR

    if _EMBEDDER is not None or _EMBEDDING_INIT_ERROR is not None:
        return

    try:
        st_module = importlib.import_module("sentence_transformers")
        SentenceTransformer = getattr(st_module, "SentenceTransformer")

        embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        template_texts: list[str] = []
        template_intents: list[str] = []
        for intent, templates in INTENT_TEMPLATES.items():
            for template in templates:
                template_texts.append(_normalize_question(template))
                template_intents.append(intent)

        template_embeddings = embedder.encode(
            template_texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        _EMBEDDER = embedder
        _EMBEDDING_TEMPLATE_MAT = template_embeddings
        _EMBEDDING_TEMPLATE_INTENTS = template_intents
    except Exception as exc:
        _EMBEDDING_INIT_ERROR = str(exc)


def _embedding_intent_match(question: str) -> tuple[str, float] | None:
    _init_embedding_matcher()
    if _EMBEDDER is None or _EMBEDDING_TEMPLATE_MAT is None or not _EMBEDDING_TEMPLATE_INTENTS:
        return None

    q_embedding = _EMBEDDER.encode(
        [_normalize_question(question)],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0]
    scores = _EMBEDDING_TEMPLATE_MAT @ q_embedding
    best_idx = int(np.argmax(scores))
    return _EMBEDDING_TEMPLATE_INTENTS[best_idx], float(scores[best_idx])


def _semantic_intent_match(question: str) -> tuple[str, float, str]:
    embedding_result = _embedding_intent_match(question)
    if embedding_result is not None:
        intent, score = embedding_result
        return intent, score, "embedding"

    q_tokens = _tokenize(question)
    best_intent = "unknown"
    best_score = 0.0
    for intent, templates in INTENT_TEMPLATES.items():
        for template in templates:
            score = _jaccard(q_tokens, _tokenize(template))
            if score > best_score:
                best_score = score
                best_intent = intent
    return best_intent, best_score, "jaccard"


def _extract_variables(question: str) -> list[str]:
    q = _normalize_question(question)
    found: list[str] = []
    for alias, canonical in DEFAULT_LABEL_ALIASES.items():
        if alias in q and canonical not in found:
            found.append(canonical)
    return found


def parse_intent_node(state: RouterState) -> RouterState:
    q = _normalize_question(state["question"])
    vars_found = _extract_variables(q)

    intent = "unknown"
    entities: dict[str, Any] = {"variables": vars_found}

    has_when = ("when" in q) or ("what time" in q) or ("time of" in q)
    has_where = ("where" in q) or ("location" in q) or ("position" in q) or ("place" in q)
    has_max = ("highest" in q) or ("maximum" in q) or ("max" in q) or ("peak" in q)
    has_min = ("lowest" in q) or ("minimum" in q) or ("min" in q)

    if has_when and has_max:
        intent = "when_max"
    elif has_where and has_max:
        intent = "where_max"
    elif has_when and has_min:
        intent = "when_min"
    elif has_where and has_min:
        intent = "where_min"
    elif ("lag" in q and "correlation" in q) or ("best lag" in q):
        intent = "lag_correlation"
    elif "correlation" in q:
        intent = "correlation"
    elif ("decrease" in q or "decreasing" in q or "increase" in q or "increasing" in q) and len(vars_found) >= 2:
        intent = "relationship_direction"
    elif (("list" in q) and ("variable" in q)) or ("what variables" in q) or ("available variables" in q):
        intent = "list_variables"
    elif (("summary" in q) and ("stat" in q)) or ("mean value" in q) or ("stats" in q):
        intent = "summary_stats"
    elif ("time series" in q and len(vars_found) >= 1) or ("timeseries" in q and len(vars_found) >= 1) or ("fetch" in q and len(vars_found) >= 1):
        intent = "timeseries_fetch"
    elif "trend" in q or ("slope" in q and len(vars_found) >= 1):
        intent = "trend"
    elif ("anomaly" in q) or ("outlier" in q):
        intent = "anomaly_detection"
    elif ("timestamp" in q and "align" in q) or ("alignment" in q):
        intent = "timestamp_alignment"
    elif ("gap" in q or "missing interval" in q) and len(vars_found) >= 1:
        intent = "data_gaps"
    elif (("qc" in q) or ("quality control" in q)) and len(vars_found) >= 1:
        intent = "sensor_qc"
    elif ("speed summary" in q) or ("distance speed" in q) or ("speed" in q and "track" in q):
        intent = "speed_summary"
    elif ("join" in q and "geo" in q) or ("join" in q and "location" in q and len(vars_found) >= 1):
        intent = "geo_join"
    elif ("ctd" in q and "profile" in q) or ("depth-binned" in q and "ctd" in q):
        intent = "ctd_profile_summary"
    elif ("mixed layer" in q) or ("mld" in q):
        intent = "ctd_mld"
    elif "thermocline" in q:
        intent = "ctd_thermocline"
    elif ("mean" in q or "average" in q) and len(vars_found) >= 1:
        intent = "mean"
    elif ("median" in q or "middle value" in q) and len(vars_found) >= 1:
        intent = "median"
    elif ("mode" in q or "most frequent" in q or "modal" in q) and len(vars_found) >= 1:
        intent = "mode"
    elif ("bounds" in q or "min and max" in q or "range" in q or "minimum and maximum" in q) and len(vars_found) >= 1:
        intent = "bounds"

    if intent == "unknown":
        semantic_intent, semantic_score, semantic_method = _semantic_intent_match(q)
        threshold = EMBEDDING_SCORE_THRESHOLD if semantic_method == "embedding" else JACCARD_SCORE_THRESHOLD
        if semantic_score >= threshold:
            intent = semantic_intent
            entities["semantic_score"] = semantic_score
            entities["semantic_method"] = semantic_method
            entities["semantic_threshold"] = threshold

    if intent in {"when_max", "where_max", "when_min", "where_min"} and vars_found:
        entities["variable"] = vars_found[0]
    if intent == "correlation" and len(vars_found) >= 2:
        entities["x"] = vars_found[0]
        entities["y"] = vars_found[1]
    if intent == "relationship_direction" and len(vars_found) >= 2:
        entities["x"] = vars_found[1]
        entities["y"] = vars_found[0]
    if intent == "lag_correlation" and len(vars_found) >= 2:
        entities["x"] = vars_found[0]
        entities["y"] = vars_found[1]
    if intent in {"summary_stats", "timeseries_fetch", "trend", "anomaly_detection", "data_gaps", "sensor_qc", "geo_join", "mean", "median", "mode", "bounds"} and vars_found:
        entities["variable"] = vars_found[0]
        entities["labels"] = vars_found[:3]

    state["intent"] = intent
    state["entities"] = entities
    return state


def execute_tool_node(state: RouterState) -> RouterState:
    try:
        intent = state.get("intent", "unknown")
        entities = state.get("entities", {})
        scalar_path = Path(state["scalar_path"])
        geo_path = Path(state["geo_path"])

        if intent in {"when_max", "when_min"}:
            variable = entities.get("variable")
            if not variable:
                raise ValueError("No variable detected for 'when' extreme query.")

            mode = "max" if intent == "when_max" else "min"
            mode_word = "highest" if mode == "max" else "lowest"

            per_track, _ = where_was_extreme_tool(scalar_path, geo_path, variable, mode=mode)
            if per_track.empty:
                state["result"] = {
                    "answer_text": f"No rows found for {variable}.",
                    "table": per_track,
                }
                return state

            row = per_track.iloc[0]
            answer = f"{variable} was {mode_word} at {row['time']} with value {row['value']}."
            state["result"] = {"answer_text": answer, "table": per_track[["time", "value", "longitude", "latitude"]]}
            return state

        if intent in {"where_max", "where_min"}:
            variable = entities.get("variable")
            if not variable:
                raise ValueError("No variable detected for 'where' extreme query.")

            mode = "max" if intent == "where_max" else "min"
            mode_word = "highest" if mode == "max" else "lowest"

            per_track, mean_pos = where_was_extreme_tool(scalar_path, geo_path, variable, mode=mode)
            if mean_pos.empty:
                state["result"] = {
                    "answer_text": f"No joined location found for {mode_word} {variable}.",
                    "table": per_track,
                }
                return state

            m = mean_pos.iloc[0]
            answer = (
                f"{variable} was {mode_word} at ({m['mean_longitude']:.6f}, {m['mean_latitude']:.6f}) "
                f"at {m['time']} (value={m['value']})."
            )
            state["result"] = {"answer_text": answer, "table": per_track}
            return state

        if intent == "correlation":
            x = entities.get("x")
            y = entities.get("y")
            if not x or not y:
                raise ValueError("Need two variables for correlation query.")

            corr = correlation_tool(scalar_path, [x, y])
            if corr.empty:
                state["result"] = {"answer_text": f"No correlation result for {x} and {y}.", "table": corr}
                return state

            corr_val = float(corr.loc[x, y])
            answer = f"Correlation between {x} and {y} is {corr_val:.4f}."
            state["result"] = {"answer_text": answer, "table": corr}
            return state

        if intent == "relationship_direction":
            x = entities.get("x")
            y = entities.get("y")
            if not x or not y:
                raise ValueError("Need two variables for relationship-direction query.")

            rel = relationship_direction_tool(scalar_path, x, y)
            rel_df = pd.DataFrame([rel])

            direction = rel.get("direction", "unknown")
            n = rel.get("n", 0)
            slope = rel.get("slope_y_per_x")
            pearson_r = rel.get("pearson_r")

            if n == 0:
                answer = f"No overlapping data to assess how {y} changes with {x}."
            else:
                answer = (
                    f"{y} tends to {direction} with {x} "
                    f"(slope={slope:.6g}, Pearson r={pearson_r:.4f}, n={n})."
                )

            state["result"] = {"answer_text": answer, "table": rel_df}
            return state

        if intent == "list_variables":
            variables_df = list_variables_tool(scalar_path)
            answer = f"Found {len(variables_df)} variables in scalar dataset."
            state["result"] = {"answer_text": answer, "table": variables_df}
            return state

        if intent == "summary_stats":
            variable = entities.get("variable")
            labels = [variable] if variable else None
            stats_df = summary_stats_tool(scalar_path, labels=labels)
            if stats_df.empty:
                state["result"] = {"answer_text": "No summary stats available.", "table": stats_df}
                return state
            answer = f"Computed summary stats for {len(stats_df)} variable(s)."
            state["result"] = {"answer_text": answer, "table": stats_df}
            return state

        if intent == "timeseries_fetch":
            labels = entities.get("labels") or entities.get("variables") or []
            if not labels:
                raise ValueError("Need at least one variable for timeseries fetch.")
            ts_df = timeseries_fetch_tool(scalar_path, labels=list(labels))
            answer = f"Fetched {len(ts_df)} rows for labels: {', '.join(labels)}."
            state["result"] = {"answer_text": answer, "table": ts_df}
            return state

        if intent == "lag_correlation":
            x = entities.get("x")
            y = entities.get("y")
            if not x or not y:
                raise ValueError("Need two variables for lag correlation query.")
            lag_df, best_lag, best_corr = lag_correlation_tool(scalar_path, x, y, max_lag_steps=120)
            answer = f"Best lag between {x} and {y} is {best_lag} steps (corr={best_corr:.4f})."
            state["result"] = {"answer_text": answer, "table": lag_df}
            return state

        if intent == "trend":
            variable = entities.get("variable")
            if not variable:
                raise ValueError("Need one variable for trend query.")
            trend_info = trend_tool(scalar_path, variable, rolling_window=60)
            trend_df = pd.DataFrame([{
                "variable": variable,
                "slope": trend_info.get("slope"),
                "intercept": trend_info.get("intercept"),
                "n": trend_info.get("n"),
            }])
            answer = f"Trend for {variable}: slope={trend_info.get('slope'):.6g}, n={trend_info.get('n')}."
            state["result"] = {"answer_text": answer, "table": trend_df}
            return state

        if intent == "anomaly_detection":
            variable = entities.get("variable")
            if not variable:
                raise ValueError("Need one variable for anomaly detection query.")
            anomaly_df = anomaly_detection_tool(scalar_path, variable, z_threshold=3.0)
            answer = f"Detected {len(anomaly_df)} anomaly rows for {variable}."
            state["result"] = {"answer_text": answer, "table": anomaly_df}
            return state

        if intent == "timestamp_alignment":
            variable = entities.get("variable")
            align = timestamp_alignment_tool(scalar_path, geo_path, variable=variable)
            align_df = pd.DataFrame([align])
            answer = (
                f"Timestamp overlap={align.get('overlap')} | "
                f"scalar_covered_by_geo={align.get('scalar_covered_by_geo'):.2%}"
            )
            state["result"] = {"answer_text": answer, "table": align_df}
            return state

        if intent == "data_gaps":
            variable = entities.get("variable")
            if not variable:
                raise ValueError("Need one variable for data gap query.")
            gaps_df = data_gaps_tool(scalar_path, variable, expected_step_seconds=60)
            answer = f"Found {len(gaps_df)} gaps for {variable}."
            state["result"] = {"answer_text": answer, "table": gaps_df}
            return state

        if intent == "sensor_qc":
            variable = entities.get("variable")
            if not variable:
                raise ValueError("Need one variable for sensor QC query.")

            min_valid = None
            max_valid = None
            if variable == "Salinity":
                min_valid, max_valid = 30.0, 40.0
            elif variable == "Wind Spd":
                min_valid, max_valid = 0.0, 80.0
            elif variable in {"Temperature", "External Temp"}:
                min_valid, max_valid = -2.5, 40.0

            qc_df = sensor_qc_tool(scalar_path, variable, min_valid=min_valid, max_valid=max_valid)
            answer = f"QC flagged {len(qc_df)} rows for {variable}."
            state["result"] = {"answer_text": answer, "table": qc_df}
            return state

        if intent == "speed_summary":
            _speed_df, speed_summary_df = distance_speed_tool(geo_path)
            answer = f"Computed speed summary for {len(speed_summary_df)} navigation source(s)."
            state["result"] = {"answer_text": answer, "table": speed_summary_df}
            return state

        if intent == "geo_join":
            variable = entities.get("variable")
            if not variable:
                raise ValueError("Need one variable for geo join query.")
            joined_df = geo_join_tool(scalar_path, geo_path, variable)
            answer = f"Joined {len(joined_df)} rows for {variable} with geospatial positions."
            state["result"] = {"answer_text": answer, "table": joined_df}
            return state

        if intent in {"ctd_profile_summary", "ctd_mld", "ctd_thermocline"}:
            ctd_df = ctd_prepare_dataframe_tool(scalar_path, require_core=False)
            if ctd_df.empty:
                state["result"] = {"answer_text": "No CTD-compatible rows found.", "table": ctd_df}
                return state

            if intent == "ctd_profile_summary":
                profile_df = ctd_profile_summary_tool(ctd_df, depth_bin_m=5.0)
                answer = f"Computed CTD depth-bin profile with {len(profile_df)} bins."
                state["result"] = {"answer_text": answer, "table": profile_df}
                return state

            if intent == "ctd_mld":
                mld = mixed_layer_depth_tool(ctd_df)
                mld_df = pd.DataFrame([mld])
                answer = f"Mixed layer depth estimate: {mld.get('mld_depth_m')} m ({mld.get('reason')})."
                state["result"] = {"answer_text": answer, "table": mld_df}
                return state

            thermo = thermocline_depth_tool(ctd_df)
            thermo_df = pd.DataFrame([thermo])
            answer = f"Thermocline depth estimate: {thermo.get('thermocline_depth_m')} m ({thermo.get('reason')})."
            state["result"] = {"answer_text": answer, "table": thermo_df}
            return state


        if intent == "mean":
            labels = entities.get("labels") or entities.get("variables") or []
            if not labels:
                raise ValueError("Need at least one variable for mean calculation.")
            mean_df = mean_tool(scalar_path, labels=list(labels))
            if mean_df.empty:
                state["result"] = {"answer_text": "No mean data available.", "table": mean_df}
                return state
            answer = f"Computed mean for {len(mean_df)} variable(s)."
            state["result"] = {"answer_text": answer, "table": mean_df}
            return state

        if intent == "median":
            labels = entities.get("labels") or entities.get("variables") or []
            if not labels:
                raise ValueError("Need at least one variable for median calculation.")
            median_df = median_tool(scalar_path, labels=list(labels))
            if median_df.empty:
                state["result"] = {"answer_text": "No median data available.", "table": median_df}
                return state
            answer = f"Computed median for {len(median_df)} variable(s)."
            state["result"] = {"answer_text": answer, "table": median_df}
            return state

        if intent == "mode":
            labels = entities.get("labels") or entities.get("variables") or []
            if not labels:
                raise ValueError("Need at least one variable for mode calculation.")
            mode_df = mode_tool(scalar_path, labels=list(labels))
            if mode_df.empty:
                state["result"] = {"answer_text": "No mode data available.", "table": mode_df}
                return state
            answer = f"Computed mode for {len(mode_df)} variable(s)."
            state["result"] = {"answer_text": answer, "table": mode_df}
            return state

        if intent == "bounds":
            labels = entities.get("labels") or entities.get("variables") or []
            if not labels:
                raise ValueError("Need at least one variable for bounds calculation.")
            bounds_df = bounds_tool(scalar_path, labels=list(labels))
            if bounds_df.empty:
                state["result"] = {"answer_text": "No bounds data available.", "table": bounds_df}
                return state
            answer = f"Computed bounds for {len(bounds_df)} variable(s)."
            state["result"] = {"answer_text": answer, "table": bounds_df}
            return state
        state["result"] = {
            "answer_text": (
                "I could not route this query yet. Supported intents include: "
                "when/where max|min, correlation, list variables, summary stats, timeseries fetch, "
                "lag correlation, trend, anomaly detection, timestamp alignment, data gaps, sensor qc, "
                "speed summary, geo join, relationship direction, mean, median, mode, bounds, "
                "and CTD profile/MLD/thermocline."
            ),
            "table": None,
        }
        return state

    except Exception as exc:
        state["error"] = str(exc)
        return state


def finalize_node(state: RouterState) -> RouterState:
    if state.get("error"):
        state["result"] = {
            "answer_text": f"Router error: {state['error']}",
            "table": None,
        }
    return state


def _build_graph():
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise ImportError(
            "LangGraph is not installed. Install with: pip install langgraph"
        ) from exc

    graph = StateGraph(RouterState)
    graph.add_node("parse", parse_intent_node)
    graph.add_node("execute", execute_tool_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "execute")
    graph.add_edge("execute", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


def run_query(question: str, scalar_path: str | Path, geo_path: str | Path) -> RouterResult:
    app = _build_graph()
    out = app.invoke(
        {
            "question": question,
            "scalar_path": str(scalar_path),
            "geo_path": str(geo_path),
        }
    )

    result = out.get("result", {})
    return RouterResult(
        intent=out.get("intent", "unknown"),
        entities=out.get("entities", {}),
        answer_text=result.get("answer_text", "No answer."),
        table=result.get("table"),
    )
