import importlib.util
import unittest
from unittest.mock import patch

import pandas as pd

import query_router_poc.router as router


LANGGRAPH_AVAILABLE = importlib.util.find_spec("langgraph") is not None


@unittest.skipUnless(LANGGRAPH_AVAILABLE, "langgraph is required for run_query end-to-end tests")
class TestRunQueryEndToEnd(unittest.TestCase):
    @patch("query_router_poc.router.where_was_extreme_tool")
    def test_run_query_where_max(self, mock_where):
        per_track = pd.DataFrame(
            [
                {
                    "time": "2021-07-04T12:00:00+00:00",
                    "value": 34.2,
                    "longitude": -122.1,
                    "latitude": 47.6,
                    "source_file": "mock_nav",
                }
            ]
        )
        mean_pos = pd.DataFrame(
            [
                {
                    "time": "2021-07-04T12:00:00+00:00",
                    "value": 34.2,
                    "mean_longitude": -122.1,
                    "mean_latitude": 47.6,
                }
            ]
        )
        mock_where.return_value = (per_track, mean_pos)

        result = router.run_query(
            "where was salinity the highest",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "where_max")
        self.assertIn("Salinity was highest", result.answer_text)
        self.assertIsNotNone(result.table)
        self.assertEqual(len(result.table), 1)

    @patch("query_router_poc.router.correlation_tool")
    def test_run_query_correlation(self, mock_corr):
        corr_df = pd.DataFrame(
            [[1.0, 0.62], [0.62, 1.0]],
            index=["Wind Spd", "Salinity"],
            columns=["Wind Spd", "Salinity"],
        )
        mock_corr.return_value = corr_df

        result = router.run_query(
            "correlation between wind speed and salinity",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "correlation")
        self.assertIn("0.6200", result.answer_text)
        self.assertIsNotNone(result.table)
        self.assertEqual(result.table.shape, (2, 2))

    @patch("query_router_poc.router.list_variables_tool")
    def test_run_query_list_variables(self, mock_list_variables):
        mock_list_variables.return_value = pd.DataFrame(
            [
                {"sensor_label": "Salinity", "unit": "psu", "n": 100},
                {"sensor_label": "Wind Spd", "unit": "m/s", "n": 100},
            ]
        )

        result = router.run_query(
            "what variables are available",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "list_variables")
        self.assertIn("Found 2 variables", result.answer_text)
        self.assertIsNotNone(result.table)
        self.assertEqual(len(result.table), 2)

    @patch("query_router_poc.router.trend_tool")
    def test_run_query_trend(self, mock_trend):
        mock_trend.return_value = {"slope": 0.0123, "intercept": 31.5, "n": 240}

        result = router.run_query(
            "show trend of salinity",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "trend")
        self.assertIn("Trend for Salinity", result.answer_text)
        self.assertIsNotNone(result.table)
        self.assertEqual(int(result.table.iloc[0]["n"]), 240)

    @patch("query_router_poc.router.relationship_direction_tool")
    def test_run_query_relationship_direction(self, mock_relationship_direction):
        mock_relationship_direction.return_value = {
            "x_label": "Temperature",
            "y_label": "Salinity",
            "n": 300,
            "pearson_r": -0.58,
            "spearman_r": -0.55,
            "slope_y_per_x": -0.031,
            "direction": "decrease",
            "reason": "linear slope sign",
        }

        result = router.run_query(
            "does salinity decrease with temperature",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "relationship_direction")
        self.assertIn("Salinity tends to decrease with Temperature", result.answer_text)
        self.assertIsNotNone(result.table)
        self.assertEqual(int(result.table.iloc[0]["n"]), 300)

    @patch("query_router_poc.router._embedding_intent_match", return_value=("where_min", 0.91))
    @patch("query_router_poc.router.where_was_extreme_tool")
    def test_run_query_semantic_embedding_path(self, mock_where, _mock_embedding):
        per_track = pd.DataFrame(
            [
                {
                    "time": "2021-07-04T09:10:00+00:00",
                    "value": 31.1,
                    "longitude": -121.2,
                    "latitude": 47.1,
                    "source_file": "mock_nav",
                }
            ]
        )
        mean_pos = pd.DataFrame(
            [
                {
                    "time": "2021-07-04T09:10:00+00:00",
                    "value": 31.1,
                    "mean_longitude": -121.2,
                    "mean_latitude": 47.1,
                }
            ]
        )
        mock_where.return_value = (per_track, mean_pos)

        result = router.run_query(
            "which site has salinity minima",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "where_min")
        self.assertEqual(result.entities.get("semantic_method"), "embedding")
        self.assertAlmostEqual(result.entities.get("semantic_score"), 0.91, places=6)
        self.assertIn("Salinity was lowest", result.answer_text)

    @patch("query_router_poc.router.mean_tool")
    def test_run_query_mean(self, mock_mean):
        mock_mean.return_value = pd.DataFrame(
            [
                {"sensor_label": "Salinity", "mean": 34.56},
                {"sensor_label": "Wind Spd", "mean": 12.34},
            ]
        )

        result = router.run_query(
            "mean of salinity and wind speed",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "mean")
        self.assertIn("Computed mean for 2 variable(s)", result.answer_text)
        self.assertIsNotNone(result.table)
        self.assertEqual(len(result.table), 2)

    @patch("query_router_poc.router.median_tool")
    def test_run_query_median(self, mock_median):
        mock_median.return_value = pd.DataFrame(
            [
                {"sensor_label": "Salinity", "median": 34.45},
            ]
        )

        result = router.run_query(
            "median salinity",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "median")
        self.assertIn("Computed median for 1 variable(s)", result.answer_text)
        self.assertIsNotNone(result.table)
        self.assertEqual(len(result.table), 1)

    @patch("query_router_poc.router.mode_tool")
    def test_run_query_mode(self, mock_mode):
        mock_mode.return_value = pd.DataFrame(
            [
                {"sensor_label": "Salinity", "mode": 34.50, "count": 5},
            ]
        )

        result = router.run_query(
            "mode of salinity",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "mode")
        self.assertIn("Computed mode for 1 variable(s)", result.answer_text)
        self.assertIsNotNone(result.table)
        self.assertEqual(len(result.table), 1)

    @patch("query_router_poc.router.bounds_tool")
    def test_run_query_bounds(self, mock_bounds):
        mock_bounds.return_value = pd.DataFrame(
            [
                {"sensor_label": "Salinity", "min_value": 30.1, "max_value": 38.5, "range": 8.4},
                {"sensor_label": "Temperature", "min_value": 8.2, "max_value": 18.9, "range": 10.7},
            ]
        )

        result = router.run_query(
            "bounds of salinity and temperature",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "bounds")
        self.assertIn("Computed bounds for 2 variable(s)", result.answer_text)
        self.assertIsNotNone(result.table)
        self.assertEqual(len(result.table), 2)

    def test_run_query_unknown_intent(self):
        result = router.run_query(
            "hello router",
            "dummy_scalar.parquet",
            "dummy_geo.parquet",
        )

        self.assertEqual(result.intent, "unknown")
        self.assertIn("could not route", result.answer_text.lower())
        self.assertIsNone(result.table)


if __name__ == "__main__":
    unittest.main()
