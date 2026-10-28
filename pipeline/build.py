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
except ImportError:
    from metrics import build_views, calculate_metrics

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


def build() -> dict[str, Any]:
    rejects: list[dict[str, Any]] = []
    sources = _provenance()
    source_map = {r.file_name: r for r in sources.itertuples(index=False)}
    # Only explicit registry entries are loaded. Every loaded file must have provenance.
    inputs = []
    context_frames = []
    raw_root = PIPELINE / "raw"
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
    _write_rejections(rejects)
    if rejects:
        raise BuildError(f"Build stopped: {len(rejects)} rejected data/provenance issue(s). See output/rejected_rows.csv")
    site_data = ROOT / "site" / "data"
    site_data.mkdir(parents=True, exist_ok=True)
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
    for name, rows in views.items(): _dump(site_data / f"{name}.json", rows)
    latest = summary[-1]
    coverage = {"start": str(data.month.min()), "end": str(data.month.max()), "months": int(data.month.nunique())}
    _dump(site_data / "summary.json", {"coverage": coverage, "latest_month": latest["month"],
                                      "latest_totals": latest, "time_series": summary})
    meta = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "schema_version":"1.0",
            "records_loaded":int(len(data)), "rejected_rows":0, "source_files":list(sources.file_name),
            "sources":sources.to_dict("records"), "coverage_start":str(data.month.min()),
            "coverage_end":str(data.month.max()), "synthetic_demo":any("SYNTHETIC" in f for f in sources.file_name),
            "method_note":"Rolling rates use ratios of aggregate flows and opening/final stock. Missing calendar months make a rolling window unavailable."}
    _dump(site_data / "meta.json", meta)
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
        print(f"Build succeeded: {result['records_loaded']} rows, {result['coverage_start']}–{result['coverage_end']}")
    except BuildError as exc:
        print(str(exc))
        raise SystemExit(1)
