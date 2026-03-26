from pathlib import Path

from analysis_tools.common import get_default_paths
from query_router_poc.router import run_query


def main():
    workspace_root = Path(__file__).resolve().parent.parent
    paths = get_default_paths(workspace_root, "2021-07-04")

    questions = [
        "when was salinity the highest",
        "where was salinity the highest",
        "what is the correlation between wind speed and salinity",
    ]

    for question in questions:
        print(f"\nQ: {question}")
        result = run_query(question, paths["scalar"], paths["geo"])
        print("Intent:", result.intent)
        print("Entities:", result.entities)
        print("Answer:", result.answer_text)
        if result.table is not None:
            print(result.table.head(5))


if __name__ == "__main__":
    main()
