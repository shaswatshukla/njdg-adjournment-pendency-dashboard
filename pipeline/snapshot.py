"""Validation and presentation metrics for the manual official pendency snapshot.

This is intentionally separate from monthly case-flow metrics: the source provides
one dated aggregate stock and one nested age-band count, not case-flow series.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pandas as pd

SNAPSHOT_COLUMNS = ["state", "court_level", "court_id", "court_label", "snapshot_date",
                    "cases_pending", "cases_pending_over_5y", "source_table"]
LEVELS = {"supreme_court", "high_court", "district_subordinate_aggregate"}
PRIVACY = re.compile(r"name|phone|aadhaar|address|party|accused", re.I)


class SnapshotError(ValueError):
    def __init__(self, message: str, rejections: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.rejections = rejections or []


def validate_snapshot(path: Path, provenance: dict[str, Any], controls: dict[str, Any]) -> dict[str, Any]:
    """Validate and summarize reported stocks, reconciling against source controls."""
    try:
        headers = list(pd.read_csv(path, nrows=0).columns)
    except Exception as exc:
        raise SnapshotError(f"Unreadable official snapshot CSV: {type(exc).__name__}") from exc
    if any(PRIVACY.search(str(c)) for c in headers):
        raise SnapshotError("Official snapshot refused: personal-data column name detected")
    missing = [c for c in SNAPSHOT_COLUMNS if c not in headers]
    extra = [c for c in headers if c not in SNAPSHOT_COLUMNS]
    if missing or extra:
        raise SnapshotError(f"Snapshot schema mismatch; missing={missing}, unexpected={extra}")
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:
        raise SnapshotError(f"Unreadable official snapshot CSV: {type(exc).__name__}") from exc
    if frame.empty:
        raise SnapshotError("Official snapshot has no data rows")
    if provenance.get("file_name") != path.relative_to(path.parents[1]).as_posix():
        # Caller should supply provenance for this exact raw-relative path.
        raise SnapshotError("Snapshot provenance file_name does not match input path")
    required_provenance = ("source_name", "source_url", "download_date", "licence", "coverage_start", "coverage_end", "notes")
    if any(not str(provenance.get(c, "")).strip() for c in required_provenance):
        raise SnapshotError("Official snapshot provenance is incomplete")
    if controls.get("source_url") != provenance.get("source_url"):
        raise SnapshotError("Official snapshot source URL does not match the registered provenance")
    as_of = controls.get("data_as_of")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(as_of or "")) or pd.isna(pd.to_datetime(as_of, format="%Y-%m-%d", errors="coerce")):
        raise SnapshotError("Official snapshot control data_as_of must be YYYY-MM-DD")
    as_of_month = str(as_of)[:7]
    if not (str(provenance["coverage_start"]) <= as_of_month <= str(provenance["coverage_end"])):
        raise SnapshotError("Official snapshot data_as_of falls outside registered provenance coverage")
    source_tables = controls.get("source_tables")
    source_pages = controls.get("source_pages")
    if (not isinstance(source_tables, dict) or any(not str(source_tables.get(level, "")).strip() for level in LEVELS)
            or not isinstance(source_pages, dict) or not source_pages):
        raise SnapshotError("Official snapshot controls require source table identifiers and page numbers")
    if any(not isinstance(page, int) or isinstance(page, bool) or page < 1 for page in source_pages.values()):
        raise SnapshotError("Official snapshot source page numbers must be positive 1-based integers")
    if not str(controls.get("source_title", "")).strip():
        raise SnapshotError("Official snapshot controls require source_title")
    errors = []
    output = []
    seen = set()
    for index, row in frame.iterrows():
        line = index + 2
        values = {c: str(row[c]).strip() for c in SNAPSHOT_COLUMNS}
        level = values["court_level"]
        if level not in LEVELS:
            errors.append({"source_file": provenance["file_name"], "row_number": line,
                           "reason": "Unknown court_level", **values}); continue
        if not values["court_id"] or not values["court_label"]:
            errors.append({"source_file": provenance["file_name"], "row_number": line,
                           "reason": "Missing court_id or court_label", **values}); continue
        if values["snapshot_date"] != as_of:
            errors.append({"source_file": provenance["file_name"], "row_number": line,
                           "reason": "Row snapshot_date differs from official controls data_as_of", **values}); continue
        if level == "district_subordinate_aggregate":
            if not values["state"]:
                errors.append({"source_file": provenance["file_name"], "row_number": line,
                               "reason": "State/UT is required for district/subordinate aggregate rows", **values}); continue
            if values["source_table"] != source_tables["district_subordinate_aggregate"]:
                errors.append({"source_file": provenance["file_name"], "row_number": line,
                               "reason": "District/subordinate aggregates cite an unexpected source table", **values}); continue
        elif values["state"] or values["source_table"] != source_tables[level]:
            errors.append({"source_file": provenance["file_name"], "row_number": line,
                           "reason": "Supreme/High Court rows cite an unexpected source table or have a state", **values}); continue
        key = (values["court_id"], values["snapshot_date"])
        if key in seen:
            errors.append({"source_file": provenance["file_name"], "row_number": line,
                           "reason": "Duplicate court_id/snapshot_date key", **values}); continue
        seen.add(key)
        for col in ("cases_pending", "cases_pending_over_5y"):
            raw = values[col]
            if not re.fullmatch(r"\d+", raw):
                errors.append({"source_file": provenance["file_name"], "row_number": line,
                               "reason": f"Invalid non-negative integer: {col}", **values}); break
            values[col] = int(raw)
        else:
            if values["cases_pending_over_5y"] > values["cases_pending"]:
                errors.append({"source_file": provenance["file_name"], "row_number": line,
                               "reason": "Over-five-year count exceeds pending count", **values}); continue
            output.append(values)
    if errors:
        raise SnapshotError(f"Official snapshot contains {len(errors)} invalid row(s): {errors[0]['reason']}", errors)

    published = controls.get("published_control_totals", {})
    by_level: dict[str, dict[str, int]] = {}
    for level in LEVELS:
        subset = [r for r in output if r["court_level"] == level]
        if len({r["court_id"] for r in subset}) != len(subset) or len({r["court_label"] for r in subset}) != len(subset):
            raise SnapshotError(f"Duplicate court_id or court_label for {level}")
        totals = {"reporting_units": len(subset),
                  "cases_pending": sum(r["cases_pending"] for r in subset),
                  "cases_pending_over_5y": sum(r["cases_pending_over_5y"] for r in subset)}
        if not subset:
            raise SnapshotError(f"No rows for required published category: {level}")
        expected = published.get(level)
        if not isinstance(expected, dict) or totals != expected:
            raise SnapshotError(f"Official source control mismatch for {level}: observed={totals}, expected={expected}")
        by_level[level] = totals
    combined = {key: sum(by_level[level][key] for level in LEVELS)
                for key in ("reporting_units", "cases_pending", "cases_pending_over_5y")}
    expected_combined = published.get("reported_categories_combined")
    if combined != expected_combined:
        raise SnapshotError(f"Official combined source controls mismatch: observed={combined}, expected={expected_combined}")

    state_rows = [r for r in output if r["court_level"] == "district_subordinate_aggregate"]
    state_labels = [r["state"] for r in state_rows]
    expected_states = controls.get("expected_state_ut_aggregate_labels")
    if not isinstance(expected_states, list) or len(state_labels) != len(set(state_labels)) or set(state_labels) != set(expected_states):
        raise SnapshotError("Reported state/UT aggregate labels do not match the controls manifest")
    for level, control_name in (("high_court", "expected_high_court_labels"),
                                ("supreme_court", "expected_supreme_court_labels")):
        expected_labels = controls.get(control_name)
        actual_labels = {r["court_label"] for r in output if r["court_level"] == level}
        if not isinstance(expected_labels, list) or actual_labels != set(expected_labels):
            raise SnapshotError(f"Reported court labels do not match the controls manifest for {level}")
    coverage_counts = controls.get("coverage_counts", {})
    observed_coverage_counts = {
        "states_and_union_territories_with_district_subordinate_aggregate": len(state_rows),
        "high_courts": by_level["high_court"]["reporting_units"],
        "supreme_courts": by_level["supreme_court"]["reporting_units"],
    }
    if coverage_counts != observed_coverage_counts:
        raise SnapshotError("Official source coverage counts do not match the controls manifest")

    def summary_metrics(counts: dict[str, int], label: str) -> dict[str, Any]:
        pending, old = counts["cases_pending"], counts["cases_pending_over_5y"]
        return {
            "cases_pending": {"value": pending, "method": f"Sum of reported pending stocks for {label}; published reporting units only"},
            "cases_pending_over_5y": {"value": old, "method": f"Sum of reported over-five-year counts for {label}; published reporting units only"},
            "share_pending_over_5y": {"value": old / pending if pending else None,
                                      "method": f"Sum of reported over-five-year counts ÷ sum of reported pending stocks for {label}; ratio of aggregate counts"},
            "pendency_rate": {"value": None, "method": "Unavailable: opening stock and monthly case flows are not reported"},
            "clearance_rate": {"value": None, "method": "Unavailable: instituted and disposed counts are not reported"},
            "adjournment_rate": {"value": None, "method": "Unavailable: hearings listed and adjourned are not reported"},
            "share_pending_over_3y": {"value": None, "method": "Unavailable: over-three-year count is not reported"},
        }
    summary_methods = {level: summary_metrics(by_level[level], level.replace("_", " ")) for level in LEVELS}
    summary_methods["reported_categories_combined"] = summary_metrics(combined, "the three reported categories combined")

    for row in output:
        pending, old = row["cases_pending"], row["cases_pending_over_5y"]
        row["metrics"] = {
            "cases_pending": {"value": pending, "method": "Reported stock in the source snapshot as of " + as_of},
            "cases_pending_over_5y": {"value": old, "method": "Reported nested age-band count in the source snapshot as of " + as_of},
            "share_pending_over_5y": {"value": old / pending if pending else None,
                                      "method": "Reported pending over 5 years ÷ reported pending; derived from this snapshot"},
            "pendency_rate": {"value": None, "method": "Unavailable: opening stock and monthly case flows are not reported"},
            "clearance_rate": {"value": None, "method": "Unavailable: instituted and disposed counts are not reported"},
            "adjournment_rate": {"value": None, "method": "Unavailable: hearings listed and adjourned are not reported"},
            "share_pending_over_3y": {"value": None, "method": "Unavailable: over-three-year count is not reported"},
            "cases_instituted": {"value": None, "method": "Unavailable: not reported in this source"},
            "cases_disposed": {"value": None, "method": "Unavailable: not reported in this source"},
            "hearings_listed": {"value": None, "method": "Unavailable: not reported in this source"},
            "hearings_adjourned": {"value": None, "method": "Unavailable: not reported in this source"},
            "rolling_3m": {"value": None, "method": "Unavailable: a single dated snapshot is not a time series"},
        }
    return {
        "schema_version": "1.0",
        "data_as_of": as_of,
        "records": output,
        "totals_by_level": by_level,
        "reported_categories_combined": combined,
        "summary_metrics": summary_methods,
        "coverage": {"states_and_union_territories": sorted(r["state"] for r in state_rows),
                     "state_ut_aggregate_count": len(state_rows),
                     "high_court_count": by_level["high_court"]["reporting_units"],
                     "supreme_court_count": by_level["supreme_court"]["reporting_units"],
                     "published_reporting_units": len(output),
                     "district_level_detail": False,
                     "tribunal_coverage": "Not stated in source"},
        "source": {"source_name": provenance["source_name"], "source_url": provenance["source_url"],
                   "title": controls["source_title"], "answer_date": controls.get("answer_date"),
                   "source_tables": list(dict.fromkeys(source_tables.values())),
                   "source_table_by_level": source_tables, "source_pages": source_pages,
                   "licence": provenance["licence"], "notes": provenance["notes"],
                   "csv_sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
        "limitations": controls.get("limitations", []),
        "label_aliases": controls.get("label_aliases", {}),
    }
