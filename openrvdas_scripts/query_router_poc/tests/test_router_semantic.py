import unittest
from unittest.mock import patch

import query_router_poc.router as router


class TestRouterSemanticMatching(unittest.TestCase):
    def test_rule_based_intent_takes_priority(self):
        state = {
            "question": "when was salinity the highest",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)

        self.assertEqual(out["intent"], "when_max")
        self.assertNotIn("semantic_method", out["entities"])
        self.assertEqual(out["entities"].get("variable"), "Salinity")

    def test_rule_intent_list_variables(self):
        state = {
            "question": "what variables are available",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)
        self.assertEqual(out["intent"], "list_variables")

    def test_rule_intent_trend(self):
        state = {
            "question": "show trend of salinity",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)
        self.assertEqual(out["intent"], "trend")
        self.assertEqual(out["entities"].get("variable"), "Salinity")

    def test_rule_intent_relationship_direction(self):
        state = {
            "question": "does salinity decrease with temperature",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)
        self.assertEqual(out["intent"], "relationship_direction")
        self.assertEqual(out["entities"].get("x"), "Temperature")
        self.assertEqual(out["entities"].get("y"), "Salinity")

    @patch("query_router_poc.router._embedding_intent_match", return_value=("where_min", 0.81))
    def test_embedding_semantic_match_used_for_unknown_rule(self, _mock_embedding):
        state = {
            "question": "which site has salinity minima",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)

        self.assertEqual(out["intent"], "where_min")
        self.assertEqual(out["entities"].get("semantic_method"), "embedding")
        self.assertAlmostEqual(out["entities"].get("semantic_score"), 0.81, places=6)
        self.assertEqual(out["entities"].get("semantic_threshold"), router.EMBEDDING_SCORE_THRESHOLD)
        self.assertEqual(out["entities"].get("variable"), "Salinity")

    @patch("query_router_poc.router._embedding_intent_match", return_value=("where_max", 0.2))
    def test_embedding_below_threshold_does_not_route(self, _mock_embedding):
        state = {
            "question": "position of salinity",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)

        self.assertEqual(out["intent"], "unknown")
        self.assertNotIn("semantic_method", out["entities"])

    @patch("query_router_poc.router._embedding_intent_match", return_value=None)
    def test_jaccard_fallback_method_recorded(self, _mock_embedding):
        state = {
            "question": "site of minimum salinity",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)

        self.assertIn(out["intent"], {"where_min", "when_min"})
        self.assertEqual(out["entities"].get("semantic_method"), "jaccard")
        self.assertGreaterEqual(out["entities"].get("semantic_score", 0.0), router.JACCARD_SCORE_THRESHOLD)
        self.assertEqual(out["entities"].get("semantic_threshold"), router.JACCARD_SCORE_THRESHOLD)


    def test_rule_intent_mean(self):
        state = {
            "question": "mean of salinity",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)
        self.assertEqual(out["intent"], "mean")
        self.assertEqual(out["entities"].get("labels"), ["Salinity"])

    def test_rule_intent_median(self):
        state = {
            "question": "median wind speed",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)
        self.assertEqual(out["intent"], "median")
        self.assertEqual(out["entities"].get("labels"), ["Wind Spd"])

    def test_rule_intent_mode(self):
        state = {
            "question": "mode of salinity",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)
        self.assertEqual(out["intent"], "mode")
        self.assertEqual(out["entities"].get("labels"), ["Salinity"])

    def test_rule_intent_bounds(self):
        state = {
            "question": "bounds of temperature",
            "scalar_path": "dummy_scalar.parquet",
            "geo_path": "dummy_geo.parquet",
        }

        out = router.parse_intent_node(state)
        self.assertEqual(out["intent"], "bounds")
        self.assertEqual(out["entities"].get("labels"), ["Temperature"])


if __name__ == "__main__":
    unittest.main()
