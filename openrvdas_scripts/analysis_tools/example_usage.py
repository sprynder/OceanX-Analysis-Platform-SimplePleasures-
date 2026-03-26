from pathlib import Path

from analysis_tools.common import get_default_paths
from analysis_tools.query_tools import (
    list_variables_tool,
    where_was_extreme_tool,
)
from analysis_tools.analysis import (
    correlation_tool,
    trend_tool,
)
from analysis_tools.qc_tools import timestamp_alignment_tool
from analysis_tools.ctd_tools import (
    ctd_detect_variable_labels_tool,
    ctd_prepare_dataframe_tool,
    ctd_profile_segments_tool,
    ctd_profile_summary_tool,
    mixed_layer_depth_tool,
    thermocline_depth_tool,
    ctd_qc_tool,
)


def main():
    workspace_root = Path(__file__).resolve().parent.parent
    paths = get_default_paths(workspace_root, "2021-07-04")

    print("Variables")
    print(list_variables_tool(paths["scalar"]).head(10))

    print("\nWhere was salinity highest?")
    per_track, mean_pos = where_was_extreme_tool(paths["scalar"], paths["geo"], "Salinity", mode="max")
    print(per_track)
    print(mean_pos)

    print("\nCorrelation (Wind Spd, Salinity)")
    print(correlation_tool(paths["scalar"], ["Wind Spd", "Salinity"]))

    print("\nTrend (Wind Spd)")
    print(trend_tool(paths["scalar"], "Wind Spd", rolling_window=60)["slope"])

    print("\nTimestamp alignment")
    print(timestamp_alignment_tool(paths["scalar"], paths["geo"], variable="Salinity"))

    print("\nCTD label detection")
    print(ctd_detect_variable_labels_tool(paths["scalar"]))

    ctd_df = ctd_prepare_dataframe_tool(paths["scalar"], require_core=False)
    print("\nCTD prepared dataframe")
    print(ctd_df.head(10))

    if not ctd_df.empty and ctd_df["depth"].notna().any() and ctd_df["temperature"].notna().any():
        print("\nCTD cast segments")
        print(ctd_profile_segments_tool(ctd_df).head(10))

        print("\nCTD profile summary")
        print(ctd_profile_summary_tool(ctd_df, depth_bin_m=5.0).head(10))

        print("\nMixed Layer Depth")
        print(mixed_layer_depth_tool(ctd_df))

        print("\nThermocline depth")
        print(thermocline_depth_tool(ctd_df))

        print("\nCTD QC flags")
        print(ctd_qc_tool(ctd_df).head(10))
    else:
        print("\nCTD depth/temperature not available in this scalar dataset yet.")


if __name__ == "__main__":
    main()
