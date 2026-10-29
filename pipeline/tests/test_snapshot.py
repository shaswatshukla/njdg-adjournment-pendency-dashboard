import csv
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.snapshot import SnapshotError, validate_snapshot


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = Path(__file__).resolve().parents[2]
        # Fixed regression fixture pins the original 2026-03 transcription and controls.
        cls.csv_path = cls.project / "pipeline" / "tests" / "fixtures" / "raw" / "official" / "pendency_2026-03-13.csv"
        cls.controls = json.loads((cls.project / "pipeline" / "tests" / "fixtures" / "official_snapshot_controls_2026-03-13.json").read_text(encoding="utf-8"))
        cls.active_csv_path = cls.project / "pipeline" / "raw" / "official" / "pendency_2026-03-13.csv"
        cls.active_controls = json.loads((cls.project / "pipeline" / "official_snapshot_controls.json").read_text(encoding="utf-8"))
        with (cls.project / "pipeline" / "sources.csv").open(encoding="utf-8", newline="") as source:
            cls.sources = {r["file_name"]: r for r in csv.DictReader(source)}
        cls.provenance = cls.sources["official/pendency_2026-03-13.csv"]

    def test_exact_62_rows_and_all_source_controls_reconcile(self):
        result = validate_snapshot(self.csv_path, self.provenance, self.controls)
        for level, expected in self.controls["published_control_totals"].items():
            observed=result["reported_categories_combined"] if level=="reported_categories_combined" else result["totals_by_level"][level]
            self.assertEqual(observed, expected)
        self.assertEqual(len(result["records"]), self.controls["published_control_totals"]["reported_categories_combined"]["reporting_units"])
        self.assertEqual(result["coverage"]["states_and_union_territories"], self.controls["expected_state_ut_aggregate_labels"])

    def test_active_snapshot_reconciles_to_its_current_controls_and_as_of(self):
        active_source = self.sources[self.active_controls["source_file"]]
        result = validate_snapshot(self.active_csv_path, active_source, self.active_controls)
        self.assertEqual(result["data_as_of"], self.active_controls["data_as_of"])
        for level, expected in self.active_controls["published_control_totals"].items():
            observed = result["reported_categories_combined"] if level == "reported_categories_combined" else result["totals_by_level"][level]
            self.assertEqual(observed, expected)

    def test_coordinated_future_snapshot_and_controls_are_accepted(self):
        with tempfile.TemporaryDirectory(dir=self.project) as directory:
            root = Path(directory)
            raw_path = root / "raw" / "official" / "future.csv"
            raw_path.parent.mkdir(parents=True)
            with self.csv_path.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source)); fields = list(rows[0])
            old_value = int(rows[0]["cases_pending"])
            rows[0]["cases_pending"] = str(old_value + 1)
            for row in rows:
                row["snapshot_date"] = "2027-06-15"
                row["source_table"] = "Appendix A" if row["court_level"] != "district_subordinate_aggregate" else "Appendix B"
            with raw_path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
            controls = json.loads(json.dumps(self.controls))
            controls["data_as_of"] = "2027-06-15"
            controls["answer_date"] = "2027-06-20"
            controls["source_title"] = "Ministry of Justice reply to Parliamentary Question Q1"
            controls["source_url"] = "https://example.test/future-report.pdf"
            controls["source_tables"] = {"supreme_court": "Appendix A", "high_court": "Appendix A",
                                          "district_subordinate_aggregate": "Appendix B"}
            controls["source_pages"] = {"Appendix A": 11, "Appendix B": 12}
            controls["published_control_totals"]["supreme_court"]["cases_pending"] += 1
            controls["published_control_totals"]["reported_categories_combined"]["cases_pending"] += 1
            provenance = {**self.provenance, "file_name": "official/future.csv",
                          "source_url": controls["source_url"], "coverage_start": "2027-06", "coverage_end": "2027-06"}
            result = validate_snapshot(raw_path, provenance, controls)
            self.assertEqual(result["data_as_of"], "2027-06-15")
            self.assertEqual(result["source"]["title"], controls["source_title"])
            self.assertEqual(result["source"]["source_pages"], controls["source_pages"])
            self.assertEqual(result["source"]["answer_date"], controls["answer_date"])
            self.assertEqual(result["reported_categories_combined"]["cases_pending"],
                             self.controls["published_control_totals"]["reported_categories_combined"]["cases_pending"] + 1)

    def test_unreported_flow_metrics_are_none_and_shares_have_methods(self):
        result = validate_snapshot(self.csv_path, self.provenance, self.controls)
        combined=self.controls["published_control_totals"]["reported_categories_combined"]
        self.assertAlmostEqual(result["summary_metrics"]["reported_categories_combined"]["share_pending_over_5y"]["value"], combined["cases_pending_over_5y"] / combined["cases_pending"])
        self.assertIn("ratio of aggregate counts", result["summary_metrics"]["reported_categories_combined"]["share_pending_over_5y"]["method"])
        for row in result["records"]:
            for key in ("cases_instituted", "cases_disposed", "hearings_listed", "hearings_adjourned",
                        "pendency_rate", "clearance_rate", "adjournment_rate", "share_pending_over_3y", "rolling_3m"):
                self.assertIsNone(row["metrics"][key]["value"])

    def _mutated_file(self, edit):
        with tempfile.TemporaryDirectory(dir=self.project) as directory:
            temp = Path(directory) / "snapshot.csv"
            with self.csv_path.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source)); fields = list(rows[0])
            edit(rows, fields)
            with temp.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
            provenance = {**self.provenance, "file_name": "official/snapshot.csv"}
            temp_path = Path(directory) / "raw" / "official" / "snapshot.csv"
            temp_path.parent.mkdir(parents=True)
            temp.replace(temp_path)
            return validate_snapshot(temp_path, provenance, self.controls)

    def test_missing_state_label_rejects_even_when_numeric_totals_stay_same(self):
        def edit(rows, fields):
            rows[-1]["state"] = rows[-2]["state"]
            rows[-1]["court_id"] = "DIST-NEW-IDENTIFIER"
        with self.assertRaisesRegex(SnapshotError, "state/UT aggregate labels"):
            self._mutated_file(edit)

    def test_missing_provenance_coverage_for_snapshot_rejected(self):
        provenance = {**self.provenance, "coverage_start": "2026-02", "coverage_end": "2026-02"}
        with self.assertRaisesRegex(SnapshotError, "outside registered provenance coverage"):
            validate_snapshot(self.csv_path, provenance, self.controls)

    def test_age_count_cannot_exceed_pending(self):
        def edit(rows, fields):
            rows[0]["cases_pending_over_5y"] = str(int(rows[0]["cases_pending"]) + 1)
        with self.assertRaisesRegex(SnapshotError, "Over-five-year count exceeds pending"):
            self._mutated_file(edit)

    def test_duplicate_court_snapshot_key_rejected(self):
        def edit(rows, fields):
            rows[1]["court_id"] = rows[0]["court_id"]
        with self.assertRaisesRegex(SnapshotError, "invalid row.*Duplicate court_id"):
            self._mutated_file(edit)

    def test_personal_column_refused_from_header(self):
        with tempfile.TemporaryDirectory(dir=self.project) as directory:
            path = Path(directory) / "private.csv"
            path.write_text("state,court_level,name\nSECRET PERSON,high_court,SECRET PERSON\n", encoding="utf-8")
            with self.assertRaisesRegex(SnapshotError, "personal-data column") as caught:
                validate_snapshot(path, self.provenance, self.controls)
            self.assertNotIn("SECRET PERSON", str(caught.exception))
