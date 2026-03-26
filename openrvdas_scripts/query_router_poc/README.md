# LangGraph Query Router POC

Minimal router POC for scientific questions over OpenRVDAS-derived Parquet files.

## Supported intents (v1)

- `when max` (example: "when was salinity the highest")
- `where max` (example: "where was salinity the highest")
- `correlation` (example: "correlation between wind speed and salinity")

## Install

```bash
pip install langgraph
```

## Run demo

```bash
python -m query_router_poc.demo
```

The demo uses `data/cruise_2021_07_04/` parquet outputs by default.
