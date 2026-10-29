"""Validate aggregate CSV inputs and generate static-site JSON."""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:  # package import for tests; script import for `python pipeline/build.py`
    from .metrics import build_views, calculate_metrics
    from .snapshot import SnapshotError, validate_snapshot
    from .research import CRIME_FILE, load_crime, archive_snapshot
    from .periodic import load_periodic
except ImportError:
    from metrics import build_views, calculate_metrics
    from snapshot import SnapshotError, validate_snapshot
    from research import CRIME_FILE, load_crime, archive_snapshot
    from periodic import load_periodic

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "pipeline"
REQUIRED = ["state", "district", "court_type", "case_category", "month", "cases_pending_start",
            "cases_instituted", "cases_disposed", "hearings_listed", "hearings_adjourned",
            "cases_pending_over_3y", "cases_pending_over_5y"]
COUNT_COLUMNS = REQUIRED[5:]
KEY = REQUIRED[:5]
SOURCES_REQUIRED = ["file_name", "source_name", "source_url", "download_date", "licence",
                    "coverage_start", "coverage_end", "notes"]
PRIVACY = re.compile(r"name|phone|aadhaar|address|party|accused", re.I)
REFRESH_STATUSES = {"verified_snapshot", "no_change", "updated", "needs_review", "error"}


class BuildError(RuntimeError):
    pass


def _safe_rejections(rows: list[dict[str, Any]]) -> pd.DataFrame:
    # Dynamic sanitized aggregate fields make rejected rows auditable. Personal files are
    # refused before row values are ever parsed, so none of their contents can enter this log.
    columns = ["source_file", "row_number", "reason"]
    for row in rows:
        columns.extend(k for k in row if k not in columns)
    return pd.DataFrame(rows, columns=columns)


def _write_rejections(rows: list[dict[str, Any]]) -> None:
    path = PIPELINE / "output" / "rejected_rows.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    _safe_rejections(rows).to_csv(path, index=False)


def _provenance() -> pd.DataFrame:
    path = PIPELINE / "sources.csv"
    if not path.exists():
        _write_rejections([{"source_file": "sources.csv", "row_number": "", "reason": "Missing source provenance registry"}])
        raise BuildError("Missing source provenance registry: sources.csv")
    src = pd.read_csv(path, dtype=str).fillna("")
    missing = [c for c in SOURCES_REQUIRED if c not in src.columns]
    if missing:
        _write_rejections([{"source_file": "sources.csv", "row_number": "", "reason": "Provenance registry missing columns: " + ", ".join(missing)}])
        raise BuildError("sources.csv missing columns: " + ", ".join(missing))
    bad = src["file_name"].str.strip().eq("") | src["source_name"].str.strip().eq("") | src["source_url"].str.strip().eq("") | src["licence"].str.strip().eq("")
    if bad.any():
        _write_rejections([{"source_file": "sources.csv", "row_number": int(i) + 2, "reason": "Incomplete provenance entry"} for i in src.index[bad]])
        raise BuildError("Every provenance row needs file_name, source_name, source_url, and licence")
    if src.file_name.duplicated().any():
        _write_rejections([{"source_file": "sources.csv", "row_number": "", "reason": "Duplicate file_name entries in provenance registry"}])
        raise BuildError("sources.csv has duplicate file_name entries")
    valid_date = src.download_date.map(lambda v: bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)) and pd.notna(pd.to_datetime(v, format="%Y-%m-%d", errors="coerce")))
    valid_coverage = src.coverage_start.map(lambda v: bool(re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", v))) & src.coverage_end.map(lambda v: bool(re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", v)))
    if not valid_date.all() or not valid_coverage.all():
        _write_rejections([{"source_file": src.iloc[i].file_name, "row_number": "", "reason": "Provenance dates must use YYYY-MM-DD / YYYY-MM format"} for i in src.index[~(valid_date & valid_coverage)]])
        raise BuildError("Invalid provenance dates; see pipeline/output/rejected_rows.csv")
    if (src.coverage_start > src.coverage_end).any():
        _write_rejections([{"source_file": src.iloc[i].file_name, "row_number": "", "reason": "Coverage start is after coverage end"} for i in src.index[src.coverage_start > src.coverage_end]])
        raise BuildError("Invalid provenance coverage range")
    return src


def _load_file(path: Path, reject: list[dict[str, Any]]) -> pd.DataFrame:
    # Read headers before data. If any personal identifier column exists, refuse the whole file
    # without retaining or logging any of its values.
    try:
        header = list(pd.read_csv(path, nrows=0).columns)
    except Exception as exc:
        reject.append({"source_file": path.name, "row_number": "", "reason": f"Unreadable CSV: {type(exc).__name__}"})
        return pd.DataFrame()
    if any(PRIVACY.search(str(c)) for c in header):
        reject.append({"source_file": path.name, "row_number": "", "reason": "File refused: personal-data column name detected"})
        return pd.DataFrame()
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        reject.append({"source_file": path.name, "row_number": "", "reason": "Missing required columns: " + ", ".join(missing)})
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:
        reject.append({"source_file": path.name, "row_number": "", "reason": f"Unreadable CSV: {type(exc).__name__}"})
        return pd.DataFrame()
    accepted: list[dict[str, Any]] = []
    for i, record in enumerate(frame.to_dict("records"), start=2):
        reason = None
        for col in REQUIRED:
            if str(record.get(col, "")).strip() == "":
                reason = f"Missing value: {col}"; break
        if reason is None and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", record["month"].strip()):
            reason = "Invalid month; expected YYYY-MM"
        if reason is None:
            for col in COUNT_COLUMNS:
                val = record[col].strip()
                if not re.fullmatch(r"-?\d+(?:\.\d+)?", val):
                    reason = f"Non-numeric count: {col}"; break
                num = float(val)
                if num < 0:
                    reason = f"Negative count: {col}"; break
                if not num.is_integer():
                    reason = f"Count must be an integer: {col}"; break
                record[col] = int(num)
        if reason is None:
            try:
                calculate_metrics(**{c: record[c] for c in COUNT_COLUMNS})
            except ValueError as exc:
                reason = str(exc)
        if reason:
            reject.append({"source_file": path.name, "row_number": i, "reason": reason,
                           **{c: record.get(c, "") for c in REQUIRED}})
        else:
            for c in REQUIRED[:5]: record[c] = record[c].strip()
            record["_source_file"] = path.name
            accepted.append(record)
    return pd.DataFrame(accepted)


def _json_default(value: Any):
    if hasattr(value, "item"): return value.item()
    raise TypeError(f"Cannot JSON encode {type(value)}")


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")


def _refresh_status() -> dict[str, Any]:
    path = PIPELINE / "refresh_status.json"
    if not path.is_file():
        raise BuildError("Missing pipeline/refresh_status.json")
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BuildError("Invalid pipeline/refresh_status.json") from exc
    required = {"last_checked_at_utc", "status", "data_as_of", "sources", "note"}
    if not required.issubset(status):
        raise BuildError("Refresh status is missing required fields")
    try:
        checked = datetime.fromisoformat(str(status["last_checked_at_utc"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise BuildError("last_checked_at_utc must be an ISO 8601 UTC timestamp") from exc
    if checked.tzinfo is None or checked.utcoffset() is None or checked.utcoffset().total_seconds() != 0:
        raise BuildError("last_checked_at_utc must use UTC")
    data_as_of = str(status["data_as_of"])
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data_as_of) or pd.isna(pd.to_datetime(data_as_of, format="%Y-%m-%d", errors="coerce")):
        raise BuildError("Refresh data_as_of must be a valid YYYY-MM-DD date")
    if status["status"] not in REFRESH_STATUSES or not isinstance(status["sources"], list) or not status["sources"] or not all(isinstance(x, str) and x.startswith("https://") for x in status["sources"]) or not str(status["note"]).strip():
        raise BuildError("Refresh status fields are invalid")
    return status


def build() -> dict[str, Any]:
    rejects: list[dict[str, Any]] = []
    sources = _provenance()
    source_map = {r.file_name: r for r in sources.itertuples(index=False)}
    # Only explicit registry entries are loaded. Every loaded file must have provenance.
    inputs = []
    context_frames = []
    raw_root = PIPELINE / "raw"
    controls_path = PIPELINE / "official_snapshot_controls.json"
    if not controls_path.is_file():
        raise BuildError("Missing official_snapshot_controls.json")
    try:
        official_controls = json.loads(controls_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BuildError("Invalid official_snapshot_controls.json") from exc
    refresh_status = _refresh_status()
    official_files = []
    present_files = {p.relative_to(raw_root).as_posix() for p in raw_root.rglob("*.csv")}
    registered = set(sources.file_name)
    for filename in sorted(present_files - registered):
        rejects.append({"source_file": filename, "row_number": "", "reason": "Input file has no provenance entry in pipeline/sources.csv"})
    for filename in sorted(registered - present_files):
        rejects.append({"source_file": filename, "row_number": "", "reason": "Provenance-listed file not found under pipeline/raw/"})
    for filename in sources.file_name:
        path = raw_root / Path(filename)
        if not path.exists():
            rejects.append({"source_file": filename, "row_number": "", "reason": "Provenance-listed file not found under raw/"})
            continue
        if Path(filename).is_absolute() or ".." in Path(filename).parts or not filename.lower().endswith(".csv"):
            rejects.append({"source_file": filename, "row_number": "", "reason": "Only CSV files within raw/ are supported"})
            continue
        if "context" in Path(filename).parts:
            try:
                header = list(pd.read_csv(path, nrows=0).columns)
                if any(PRIVACY.search(str(col)) for col in header):
                    rejects.append({"source_file": filename, "row_number": "", "reason": "File refused: personal-data column name detected"})
                    continue
                c = pd.read_csv(path, keep_default_na=False)
                if len(c): context_frames.append(c)
            except Exception:
                rejects.append({"source_file": filename, "row_number": "", "reason": "Unreadable context CSV"})
            continue
        if filename == CRIME_FILE:
            continue
        if filename.startswith('periodic/'):
            continue
        if "official" in Path(filename).parts:
            official_files.append(filename)
            continue
        loaded = _load_file(path, rejects)
        if not loaded.empty: inputs.append(loaded)
    data = pd.concat(inputs, ignore_index=True) if inputs else pd.DataFrame(columns=REQUIRED + ["_source_file"])
    if not data.empty:
        duplicated = data.duplicated(KEY, keep=False)
        for idx in data.index[duplicated]:
            rejects.append({"source_file": data.loc[idx, "_source_file"], "row_number": "", "reason": "Duplicate aggregate key across input files"})
        for filename, group in data.groupby("_source_file"):
            provenance = source_map.get(filename)
            if provenance and (str(group.month.min()) < provenance.coverage_start or str(group.month.max()) > provenance.coverage_end):
                rejects.append({"source_file": filename, "row_number": "", "reason": "Observed aggregate months fall outside registered coverage_start/coverage_end"})
    # Context rows are also provenance-bound and may contain only approved aggregate context columns.
    context = pd.concat(context_frames, ignore_index=True) if context_frames else None
    if context is not None and not context.empty:
        allowed = {"state", "district", "population", "judge_strength", "budget"}
        if not set(context.columns).issubset(allowed) or not {"state", "district"}.issubset(context.columns):
            rejects.append({"source_file": "context", "row_number": "", "reason": "Context columns must be state, district, and optional population/judge_strength/budget"})
        else:
            if context[["state", "district"]].astype(str).apply(lambda c: c.str.strip().eq("")).any().any():
                rejects.append({"source_file": "context", "row_number": "", "reason": "Context state/district keys cannot be missing"})
            if context.duplicated(["state", "district"]).any():
                rejects.append({"source_file": "context", "row_number": "", "reason": "Duplicate context state/district keys"})
            for col in ("population", "judge_strength", "budget"):
                if col in context:
                    vals = pd.to_numeric(context[col], errors="coerce")
                    if vals.isna().any() or (vals < 0).any() or not vals.map(math.isfinite).all():
                        rejects.append({"source_file": "context", "row_number": "", "reason": f"Invalid context value: {col}"})
                    context[col] = vals
    official_snapshot: dict[str, Any] = {"available": False, "data_as_of": None, "records": [],
                                         "note": "No verified official snapshot is registered."}
    configured_official = official_controls.get("source_file")
    if official_files:
        if len(official_files) != 1 or official_files[0] != configured_official:
            rejects.append({"source_file": "official", "row_number": "", "reason": "Exactly the controls-manifest official source_file must be registered"})
        else:
            filename = official_files[0]
            provenance = source_map[filename]._asdict()
            source_path = raw_root / Path(filename)
            try:
                if provenance["source_url"] != official_controls.get("source_url"):
                    raise SnapshotError("Official source URL differs from controls manifest")
                official_snapshot = validate_snapshot(source_path, provenance, official_controls)
                official_snapshot["available"] = True
                if refresh_status["data_as_of"] != official_snapshot["data_as_of"]:
                    raise SnapshotError("Refresh status data_as_of differs from the last verified snapshot")
                if official_snapshot["source"]["source_url"] not in refresh_status["sources"]:
                    raise SnapshotError("Refresh status sources do not include the active official source URL")
            except SnapshotError as exc:
                rejects.extend(exc.rejections or [{"source_file": filename, "row_number": "", "reason": str(exc)}])
    elif configured_official in registered:
        # The registry-to-filesystem mismatch is already recorded above; keep a safe file-level reason.
        pass
    if refresh_status["data_as_of"] != official_controls.get("data_as_of"):
        rejects.append({"source_file": "pipeline/refresh_status.json", "row_number": "", "reason": "Refresh status data_as_of differs from controls manifest"})
    crime = {"records": [], "note": "No verified crime source registered."}
    if CRIME_FILE in source_map and (raw_root / CRIME_FILE).exists():
        try:
            crime = load_crime(raw_root / CRIME_FILE, source_map[CRIME_FILE]._asdict(),
                               official_controls['expected_state_ut_aggregate_labels'])
            crime_check = refresh_status.get('crime_check', {})
            if crime_check.get('year') != crime['year'] or crime['source']['source_url'] not in crime_check.get('sources', []):
                raise ValueError('Crime check metadata must identify the verified source and reporting year')
            checked = datetime.fromisoformat(str(crime_check.get('last_checked_at_utc', '')).replace('Z', '+00:00'))
            if checked.tzinfo is None or checked.utcoffset().total_seconds() != 0 or crime_check.get('status') not in REFRESH_STATUSES:
                raise ValueError('Crime verification status or UTC check date invalid')
        except (ValueError, KeyError) as exc:
            rejects.append({"source_file": CRIME_FILE, "row_number": "", "reason": str(exc)})
    periodic = {'records': [], 'reports': []}
    try:
        controls_path = PIPELINE / 'periodic_controls.json'
        periodic_controls = json.loads(controls_path.read_text(encoding='utf-8')) if controls_path.exists() else {}
        if set(periodic_controls) != {f for f in registered if f.startswith('periodic/')}:
            raise ValueError('Registered periodic files must exactly match reviewed periodic controls')
        periodic = load_periodic(raw_root, source_map, periodic_controls)
    except (ValueError, KeyError) as exc:
        rejects.append({'source_file': 'periodic', 'row_number': '', 'reason': str(exc)})
    _write_rejections(rejects)
    if rejects:
        raise BuildError(f"Build stopped: {len(rejects)} rejected data/provenance issue(s). See output/rejected_rows.csv")
    site_data = ROOT / "site" / "data"
    site_data.mkdir(parents=True, exist_ok=True)
    fixture_data = PIPELINE / 'output' / 'synthetic_fixture_outputs'
    fixture_data.mkdir(parents=True, exist_ok=True)
    if data.empty:
        raise BuildError("No aggregate rows loaded")
    views = build_views(data, context)
    overall = data.groupby("month", as_index=False).agg({
        "cases_pending_start":"sum", "cases_instituted":"sum", "cases_disposed":"sum",
        "hearings_listed":"sum", "hearings_adjourned":"sum", "cases_pending_over_3y":"sum", "cases_pending_over_5y":"sum"}).sort_values("month")
    summary = []
    for r in overall.itertuples(index=False):
        metrics = calculate_metrics(**{c: int(getattr(r, c)) for c in COUNT_COLUMNS})
        summary.append({"month":r.month, **{c:int(getattr(r,c)) for c in COUNT_COLUMNS},
                        "cases_pending_end":metrics["cases_pending_end"]["value"], "metrics":metrics})
    for name, rows in views.items(): _dump(fixture_data / f"{name}.json", rows)
    latest = summary[-1]
    coverage = {"start": str(data.month.min()), "end": str(data.month.max()), "months": int(data.month.nunique())}
    _dump(fixture_data / "summary.json", {"coverage": coverage, "latest_month": latest["month"],
                                      "latest_totals": latest, "time_series": summary})
    demo_sources = sources[~sources.file_name.str.startswith(("official/", "crime/", "periodic/"))]
    meta = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "schema_version":"1.0",
            "records_loaded":int(len(data)), "rejected_rows":0, "source_files":list(demo_sources.file_name),
            "sources":demo_sources.to_dict("records"), "coverage_start":str(data.month.min()),
            "coverage_end":str(data.month.max()), "synthetic_demo":True,
            "method_note":"Rolling rates use ratios of aggregate flows and opening/final stock. Missing calendar months make a rolling window unavailable."}
    _dump(fixture_data / "meta.json", meta)
    official_sources = sources[sources.file_name.str.startswith(('official/', 'crime/', 'periodic/'))]
    _dump(site_data / 'meta.json', {'generated_at_utc': meta['generated_at_utc'], 'schema_version': '1.1',
                                  'rejected_rows': 0, 'source_files': list(official_sources.file_name),
                                  'sources': official_sources.to_dict('records'),
                                  'records_by_dataset': {'national_snapshot': len(official_snapshot.get('records', [])),
                                                         'crime': len(crime.get('records', [])),
                                                         'periodic_reports': len(periodic.get('records', []))},
                                  'method_note': 'Official aggregate reports only. Datasets retain separate reporting dates and scopes.'})
    for obsolete in ('summary.json', 'by_state.json', 'by_district.json', 'by_court_type.json', 'by_category.json'):
        (site_data / obsolete).unlink(missing_ok=True)
    _dump(site_data / "official_snapshot.json", official_snapshot)
    _dump(site_data / "refresh_status.json", refresh_status)
    try:
        archive = archive_snapshot(PIPELINE / 'archive', official_snapshot) if official_snapshot.get('available') else {'snapshots': []}
    except ValueError as exc:
        raise BuildError(str(exc)) from exc
    _dump(site_data / 'snapshot_archive.json', archive)
    _dump(site_data / 'crime.json', crime)
    _dump(site_data / 'periodic_reports.json', periodic)
    # Require every expected artifact and parse it before declaring success.
    try:
        from .smoke import check_json
    except ImportError:
        from smoke import check_json
    try:
        check_json(site_data)
    except (ValueError, json.JSONDecodeError) as exc:
        raise BuildError(str(exc)) from exc
    return meta


if __name__ == "__main__":
    try:
        result = build()
        official = json.loads((ROOT / "site" / "data" / "official_snapshot.json").read_text(encoding="utf-8"))
        official_label = (f"{len(official['records'])} official reporting units as of {official['data_as_of']}"
                          if official.get("available") else "no official snapshot available")
        print(f"Build succeeded: {result['records_loaded']} offline synthetic fixture rows ({result['coverage_start']}-{result['coverage_end']}); {official_label}")
    except BuildError as exc:
        print(str(exc))
        raise SystemExit(1)
