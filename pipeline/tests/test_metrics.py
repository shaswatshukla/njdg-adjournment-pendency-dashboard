import unittest

from pipeline.metrics import calculate_metrics, month_successor


def metrics(**overrides):
    values = dict(cases_pending_start=100, cases_instituted=50, cases_disposed=40,
                  hearings_listed=80, hearings_adjourned=20,
                  cases_pending_over_3y=30, cases_pending_over_5y=10)
    values.update(overrides)
    return calculate_metrics(**values)


class MetricTests(unittest.TestCase):
    def test_all_metric_formulas_and_methods(self):
        result = metrics()
        self.assertEqual(result["cases_pending_end"]["value"], 110)
        self.assertAlmostEqual(result["pendency_rate"]["value"], 1.1)
        self.assertAlmostEqual(result["clearance_rate"]["value"], .8)
        self.assertAlmostEqual(result["adjournment_rate"]["value"], .25)
        self.assertAlmostEqual(result["share_pending_over_3y"]["value"], 30 / 110)
        self.assertAlmostEqual(result["share_pending_over_5y"]["value"], 10 / 110)
        self.assertTrue(all(isinstance(v["method"], str) and v["method"] for v in result.values()))

    def test_each_zero_denominator(self):
        cases = [
            ("pendency_rate", {"cases_pending_start": 0, "cases_pending_over_3y": 1, "cases_pending_over_5y": 1}),
            ("clearance_rate", {"cases_instituted": 0}),
            ("adjournment_rate", {"hearings_listed": 0, "hearings_adjourned": 0}),
            ("share_pending_over_3y", {"cases_pending_start": 0, "cases_instituted": 0,
                                        "cases_disposed": 0, "cases_pending_over_3y": 0, "cases_pending_over_5y": 0}),
            ("share_pending_over_5y", {"cases_pending_start": 0, "cases_instituted": 0,
                                        "cases_disposed": 0, "cases_pending_over_3y": 0,
                                        "cases_pending_over_5y": 0}),
        ]
        for key, overrides in cases:
            with self.subTest(metric=key):
                self.assertIsNone(metrics(**overrides)[key]["value"])

    def test_missing_input_dependencies(self):
        expected_none = {
            "cases_pending_start": {"cases_pending_end", "pendency_rate", "share_pending_over_3y", "share_pending_over_5y"},
            "cases_instituted": {"cases_pending_end", "pendency_rate", "share_pending_over_3y", "share_pending_over_5y"},
            "cases_disposed": {"cases_pending_end", "pendency_rate", "share_pending_over_3y", "share_pending_over_5y"},
            "hearings_listed": {"adjournment_rate"},
            "hearings_adjourned": {"adjournment_rate"},
            "cases_pending_over_3y": {"share_pending_over_3y"},
            "cases_pending_over_5y": {"share_pending_over_5y"},
        }
        for column, keys in expected_none.items():
            with self.subTest(column=column):
                result = metrics(**{column: None})
                self.assertTrue(all(result[k]["value"] is None for k in keys))

    def test_pandas_missing_sentinels_are_treated_as_missing(self):
        import math
        for missing in (float("nan"), __import__("pandas").NA):
            with self.subTest(missing=str(missing)):
                result = metrics(cases_instituted=missing)
                self.assertIsNone(result["cases_pending_end"]["value"])
                self.assertIsNone(result["clearance_rate"]["value"])

    def test_valid_rolling_aggregate_uses_flows_and_endpoint_stocks(self):
        import pandas as pd
        from pipeline.metrics import build_views
        frame = pd.DataFrame([
            dict(state="S", district="D", court_type="C", case_category="A", month="2024-01", cases_pending_start=100, cases_instituted=200, cases_disposed=100, hearings_listed=1000, hearings_adjourned=100, cases_pending_over_3y=50, cases_pending_over_5y=20),
            dict(state="S", district="D", court_type="C", case_category="A", month="2024-02", cases_pending_start=999, cases_instituted=50, cases_disposed=25, hearings_listed=10, hearings_adjourned=5, cases_pending_over_3y=100, cases_pending_over_5y=40),
            dict(state="S", district="D", court_type="C", case_category="A", month="2024-03", cases_pending_start=1000, cases_instituted=100, cases_disposed=80, hearings_listed=100, hearings_adjourned=50, cases_pending_over_3y=200, cases_pending_over_5y=70),
        ])
        rows = build_views(frame)["by_state"]
        rolling = next(r for r in rows if r["month"] == "2024-03" and r["period"] == "rolling_3m")
        self.assertEqual(rolling["cases_pending_start"], 100)
        self.assertEqual(rolling["cases_pending_end"], 1020)
        self.assertAlmostEqual(rolling["metrics"]["clearance_rate"]["value"], 205 / 350)
        self.assertAlmostEqual(rolling["metrics"]["adjournment_rate"]["value"], 155 / 1110)
        self.assertEqual(rolling["cases_pending_over_3y"], 200)
        self.assertEqual(rolling["cases_pending_over_5y"], 70)

    def test_each_negative_count_rejected(self):
        for column in ["cases_pending_start", "cases_instituted", "cases_disposed", "hearings_listed",
                       "hearings_adjourned", "cases_pending_over_3y", "cases_pending_over_5y"]:
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, "negative"):
                metrics(**{column: -1})

    def test_invariants_and_integer_counts(self):
        cases = [({"cases_disposed": 151}, "Disposals"),
                 ({"cases_pending_over_3y": 111}, "Over-three-year"),
                 ({"cases_pending_over_5y": 31}, "Over-five-year"),
                 ({"hearings_adjourned": 81}, "Adjourned"),
                 ({"cases_disposed": 1.5}, "whole numbers")]
        for overrides, message in cases:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, message):
                metrics(**overrides)

    def test_calendar_successor_rolls_year_boundary(self):
        self.assertEqual(month_successor("2024-01", -2), "2023-11")
