import csv
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from pipeline import build as build_module


def sample_row(**changes):
    row = dict(state="State", district="District", court_type="District Court", case_category="Civil",
               month="2024-01", cases_pending_start="10", cases_instituted="4", cases_disposed="3",
               hearings_listed="8", hearings_adjourned="2", cases_pending_over_3y="4", cases_pending_over_5y="1")
    row.update(changes)
    return row


def csv_for(row):
    return pd.DataFrame([row]).to_csv(index=False)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2])
        self.root = Path(self.tmp.name)
        self.pipeline = self.root / "pipeline"
        (self.pipeline / "raw").mkdir(parents=True)
        (self.pipeline / "output").mkdir()
        (self.root / "site" / "data").mkdir(parents=True)
        self.old_root, self.old_pipeline = build_module.ROOT, build_module.PIPELINE
        build_module.ROOT, build_module.PIPELINE = self.root, self.pipeline
        project = Path(__file__).resolve().parents[2]
        (self.pipeline / "official_snapshot_controls.json").write_text(
            (project / "pipeline" / "official_snapshot_controls.json").read_text(encoding="utf-8"), encoding="utf-8")
        (self.pipeline / "refresh_status.json").write_text(
            (project / "pipeline" / "refresh_status.json").read_text(encoding="utf-8"), encoding="utf-8")

    def tearDown(self):
        build_module.ROOT, build_module.PIPELINE = self.old_root, self.old_pipeline
        self.tmp.cleanup()

    def add_file(self, name="input.csv", row=None, raw=None):
        row = row or sample_row()
        path = self.pipeline / "raw" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw if raw is not None else csv_for(row), encoding="utf-8")
        registry = self.pipeline / "sources.csv"
        existing = pd.read_csv(registry) if registry.exists() else pd.DataFrame(columns=build_module.SOURCES_REQUIRED)
        existing.loc[len(existing)] = [name, "fixture", "https://example.test", "2024-01-01", "test",
                                       "2024-01", "2024-12", "test fixture"]
        existing.to_csv(registry, index=False)

    def test_synthetic_load_counts_outputs_and_json_parse(self):
        project = Path(__file__).resolve().parents[2]
        old_root, old_pipeline = build_module.ROOT, build_module.PIPELINE
        try:
            build_module.ROOT, build_module.PIPELINE = project, project / "pipeline"
            result = build_module.build()
            self.assertEqual(result["records_loaded"], 24)
            self.assertEqual((result["coverage_start"], result["coverage_end"]), ("2024-01", "2024-06"))
            self.assertEqual(result["rejected_rows"], 0)
            for name in ("summary", "by_state", "by_district", "by_court_type", "by_category", "meta"):
                self.assertIsNotNone(json.loads((project / "site" / "data" / f"{name}.json").read_text(encoding="utf-8")))
            official = json.loads((project / "site" / "data" / "official_snapshot.json").read_text(encoding="utf-8"))
            self.assertTrue(official["available"])
            controls = json.loads((project / "pipeline" / "official_snapshot_controls.json").read_text(encoding="utf-8"))
            self.assertEqual(official["coverage"]["published_reporting_units"],
                             controls["published_control_totals"]["reported_categories_combined"]["reporting_units"])
            refresh = json.loads((project / "site" / "data" / "refresh_status.json").read_text(encoding="utf-8"))
            canonical = json.loads((project / "pipeline" / "refresh_status.json").read_text(encoding="utf-8"))
            self.assertEqual(refresh["last_checked_at_utc"], canonical["last_checked_at_utc"])
            rows = json.loads((project / "site" / "data" / "by_district.json").read_text(encoding="utf-8"))
            self.assertTrue(any(r["period"] == "rolling_3m" for r in rows["slices"]))
        finally:
            build_module.ROOT, build_module.PIPELINE = old_root, old_pipeline

    def test_build_accepts_coordinated_future_official_snapshot(self):
        self.add_file(row=sample_row())
        project = Path(__file__).resolve().parents[2]
        fixture_csv = project / "pipeline" / "tests" / "fixtures" / "raw" / "official" / "pendency_2026-03-13.csv"
        official_path = self.pipeline / "raw" / "official" / "future.csv"
        official_path.parent.mkdir(parents=True)
        with fixture_csv.open(encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source)); fields = list(rows[0])
        rows[0]["cases_pending"] = str(int(rows[0]["cases_pending"]) + 1)
        for row in rows:
            row["snapshot_date"] = "2027-06-15"
        with official_path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

        controls_path = self.pipeline / "official_snapshot_controls.json"
        controls = json.loads(controls_path.read_text(encoding="utf-8"))
        controls["source_file"] = "official/future.csv"
        controls["data_as_of"] = "2027-06-15"
        controls["source_title"] = "Verified future parliamentary report"
        controls["source_url"] = "https://example.test/future.pdf"
        controls["answer_date"] = "2027-06-20"
        controls["published_control_totals"]["supreme_court"]["cases_pending"] += 1
        controls["published_control_totals"]["reported_categories_combined"]["cases_pending"] += 1
        controls_path.write_text(json.dumps(controls), encoding="utf-8")
        refresh_path = self.pipeline / "refresh_status.json"
        refresh = json.loads(refresh_path.read_text(encoding="utf-8"))
        refresh["data_as_of"] = "2027-06-15"
        refresh["sources"] = [controls["source_url"]]
        refresh_path.write_text(json.dumps(refresh), encoding="utf-8")

        registry_path = self.pipeline / "sources.csv"
        registry = pd.read_csv(registry_path)
        registry.loc[len(registry)] = ["official/future.csv", "Future verified fixture", controls["source_url"],
                                       "2027-06-21", "fixture terms", "2027-06", "2027-06", "coordinated future fixture"]
        registry.to_csv(registry_path, index=False)
        result = build_module.build()
        official = json.loads((self.root / "site" / "data" / "official_snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(result["records_loaded"], 1)
        self.assertEqual(official["data_as_of"], "2027-06-15")
        self.assertEqual(official["source"]["title"], "Verified future parliamentary report")
        self.assertEqual(official["coverage"]["published_reporting_units"],
                         controls["published_control_totals"]["reported_categories_combined"]["reporting_units"])

    def test_refresh_sources_must_include_active_official_source_url(self):
        self.add_file(row=sample_row())
        project = Path(__file__).resolve().parents[2]
        source_file = "official/pendency_2026-03-13.csv"
        source_path = project / "pipeline" / "raw" / source_file
        temp_source = self.pipeline / "raw" / source_file
        temp_source.parent.mkdir(parents=True)
        temp_source.write_bytes(source_path.read_bytes())
        registry = pd.read_csv(self.pipeline / "sources.csv")
        official_source = pd.read_csv(project / "pipeline" / "sources.csv")
        official_source = official_source[official_source.file_name == source_file].iloc[0].tolist()
        registry.loc[len(registry)] = official_source
        registry.to_csv(self.pipeline / "sources.csv", index=False)
        refresh_path = self.pipeline / "refresh_status.json"
        refresh = json.loads(refresh_path.read_text(encoding="utf-8"))
        refresh["sources"] = ["https://example.test/old-report.pdf"]
        refresh_path.write_text(json.dumps(refresh), encoding="utf-8")
        with self.assertRaisesRegex(build_module.BuildError, "rejected"):
            build_module.build()
        self.assertIn("active official source URL", (self.pipeline / "output" / "rejected_rows.csv").read_text(encoding="utf-8"))

    def test_rejected_row_fails_and_logs_reason_with_safe_fields(self):
        self.add_file(row=sample_row(cases_instituted="-4"))
        with self.assertRaisesRegex(build_module.BuildError, "rejected"):
            build_module.build()
        logged = (self.pipeline / "output" / "rejected_rows.csv").read_text()
        self.assertIn("Negative count", logged)
        self.assertIn("cases_instituted", logged)

    def test_missing_source_registry_fails_and_logs(self):
        with self.assertRaisesRegex(build_module.BuildError, "provenance"):
            build_module.build()
        self.assertIn("Missing source provenance", (self.pipeline / "output" / "rejected_rows.csv").read_text())

    def test_privacy_column_refuses_file_without_leaking_values(self):
        self.add_file(row=sample_row(name="SECRET PERSON CONTENT"))
        with self.assertRaises(build_module.BuildError):
            build_module.build()
        log = (self.pipeline / "output" / "rejected_rows.csv").read_text()
        self.assertIn("personal-data column", log)
        self.assertNotIn("SECRET PERSON CONTENT", log)

    def test_duplicate_key_across_files_fails(self):
        self.add_file(row=sample_row())
        self.add_file(name="other.csv", row=sample_row())
        with self.assertRaisesRegex(build_module.BuildError, "rejected"):
            build_module.build()
        self.assertIn("Duplicate aggregate key", (self.pipeline / "output" / "rejected_rows.csv").read_text())

    def test_unregistered_context_file_fails_provenance_check(self):
        self.add_file(row=sample_row())
        (self.pipeline / "raw" / "context").mkdir()
        (self.pipeline / "raw" / "context" / "extra.csv").write_text("state,district,population\nState,District,100\n")
        with self.assertRaisesRegex(build_module.BuildError, "rejected"):
            build_module.build()
        self.assertIn("no provenance", (self.pipeline / "output" / "rejected_rows.csv").read_text())

    def test_missing_month_and_changing_grain_make_rolling_unavailable(self):
        from pipeline.metrics import build_views
        rows = []
        for month, district in [("2024-01", "A"), ("2024-02", "A"), ("2024-03", "B")]:
            rows.append(dict(state="S", district=district, court_type="C", case_category="A", month=month,
                             cases_pending_start=10, cases_instituted=5, cases_disposed=2, hearings_listed=10,
                             hearings_adjourned=2, cases_pending_over_3y=3, cases_pending_over_5y=1))
        state_rows = build_views(pd.DataFrame(rows))["by_state"]
        march = next(r for r in state_rows if r["month"] == "2024-03" and r["period"] == "rolling_3m")
        self.assertIsNone(march["metrics"]["clearance_rate"]["value"])
        self.assertIn("coverage changes", march["metrics"]["clearance_rate"]["method"])

    def test_stock_is_derived_per_month_not_summed_over_time(self):
        from pipeline.metrics import build_views
        frame = pd.DataFrame([dict(state="S", district="D", court_type="C", case_category="A", month="2024-01",
                                   cases_pending_start=10, cases_instituted=5, cases_disposed=2, hearings_listed=10,
                                   hearings_adjourned=2, cases_pending_over_3y=3, cases_pending_over_5y=1),
                              dict(state="S", district="D", court_type="C", case_category="A", month="2024-03",
                                   cases_pending_start=13, cases_instituted=10, cases_disposed=4, hearings_listed=20,
                                   hearings_adjourned=4, cases_pending_over_3y=5, cases_pending_over_5y=2)])
        rows = build_views(frame)["by_district"]["series"]
        march = next(r for r in rows if r["month"] == "2024-03" and r["period"] == "rolling_3m")
        self.assertIsNone(march["metrics"]["clearance_rate"]["value"])
        march_monthly = next(r for r in rows if r["month"] == "2024-03" and r["period"] == "monthly")
        self.assertEqual(march_monthly["cases_pending_end"], 19)

    def test_context_joins_by_both_state_and_district_and_derives_per_lakh(self):
        from pipeline.metrics import build_views
        frame = pd.DataFrame([
            dict(state="S1", district="Shared", court_type="C", case_category="A", month="2024-01", cases_pending_start=9, cases_instituted=3, cases_disposed=2, hearings_listed=10, hearings_adjourned=2, cases_pending_over_3y=2, cases_pending_over_5y=1),
            dict(state="S2", district="Shared", court_type="C", case_category="A", month="2024-01", cases_pending_start=19, cases_instituted=3, cases_disposed=2, hearings_listed=10, hearings_adjourned=2, cases_pending_over_3y=3, cases_pending_over_5y=1),
        ])
        context = pd.DataFrame([dict(state="S1", district="Shared", population=1000),
                                dict(state="S2", district="Shared", population=2000)])
        rows = [r for r in build_views(frame, context)["by_district"]["series"] if r["period"] == "monthly"]
        rows.sort(key=lambda r: r["state"])
        self.assertEqual(rows[0]["context"]["population"], 1000)
        self.assertEqual(rows[0]["context"]["pending_per_lakh"]["value"], 1000)
        self.assertEqual(rows[1]["context"]["population"], 2000)
        self.assertEqual(rows[1]["context"]["pending_per_lakh"]["value"], 1000)
        self.assertIn("× 100,000", rows[0]["context"]["pending_per_lakh"]["method"])

    def test_duplicate_context_keys_are_rejected(self):
        from pipeline.metrics import build_views
        frame = pd.DataFrame([dict(state="S", district="D", court_type="C", case_category="A", month="2024-01", cases_pending_start=9, cases_instituted=3, cases_disposed=2, hearings_listed=10, hearings_adjourned=2, cases_pending_over_3y=2, cases_pending_over_5y=1)])
        context = pd.DataFrame([dict(state="S", district="D", population=1000), dict(state="S", district="D", population=2000)])
        with self.assertRaisesRegex(ValueError, "duplicate state/district"):
            build_views(frame, context)

    def test_nonfinite_context_number_rejects_build(self):
        self.add_file(row=sample_row())
        self.add_file(name="context/context.csv", raw="state,district,population\nState,District,inf\n")
        with self.assertRaisesRegex(build_module.BuildError, "rejected"):
            build_module.build()
        self.assertIn("Invalid context value", (self.pipeline / "output" / "rejected_rows.csv").read_text())

    def test_context_personal_column_is_refused_without_parsing_or_logging_values(self):
        self.add_file(row=sample_row())
        self.add_file(name="context/private.csv", raw="state,district,name,population\nState,District,SECRET PERSON,1000\n")
        with self.assertRaisesRegex(build_module.BuildError, "rejected"):
            build_module.build()
        logged = (self.pipeline / "output" / "rejected_rows.csv").read_text()
        self.assertIn("personal-data column", logged)
        self.assertNotIn("SECRET PERSON", logged)

    def test_refresh_status_invalid_timestamp_fails_without_build_fabricating_a_new_one(self):
        self.add_file(row=sample_row())
        status_path = self.pipeline / "refresh_status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        original = status["last_checked_at_utc"]
        status["last_checked_at_utc"] = "2026-10-29"
        status_path.write_text(json.dumps(status), encoding="utf-8")
        with self.assertRaisesRegex(build_module.BuildError, "UTC"):
            build_module.build()
        self.assertEqual(json.loads(status_path.read_text(encoding="utf-8"))["last_checked_at_utc"], "2026-10-29")
        self.assertNotEqual(original, "2026-10-29")
