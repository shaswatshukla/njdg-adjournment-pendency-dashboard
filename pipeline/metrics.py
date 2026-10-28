"""Documented aggregate metrics for court case-flow data."""
from __future__ import annotations

from calendar import monthrange
from datetime import date
import math
from typing import Any

import pandas as pd


def _ratio(numerator: float | int | None, denominator: float | int | None,
           method: str) -> dict[str, Any]:
    if numerator is None or denominator is None or denominator == 0:
        return {"value": None, "method": method + "; unavailable when denominator is zero or inputs are missing"}
    return {"value": numerator / denominator, "method": method}


def calculate_metrics(*, cases_pending_start: int | None, cases_instituted: int | None,
                      cases_disposed: int | None, hearings_listed: int | None,
                      hearings_adjourned: int | None, cases_pending_over_3y: int | None,
                      cases_pending_over_5y: int | None) -> dict[str, dict[str, Any]]:
    """Calculate the six documented metrics from aggregate counts.

    Formulas are end pending = opening pending + instituted - disposed;
    pendency = end pending / opening pending; clearance = disposed / instituted;
    adjournment = hearings adjourned / hearings listed; three-year share =
    cases pending over 3 years / end pending; five-year share = cases pending
    over 5 years / end pending. Missing dependencies and zero denominators yield
    ``None`` values with method notes. Negative and non-integer counts raise
    ``ValueError``.
    """
    counts = [cases_pending_start, cases_instituted, cases_disposed, hearings_listed,
              hearings_adjourned, cases_pending_over_3y, cases_pending_over_5y]
    counts = [None if v is None or pd.isna(v) else v for v in counts]
    cases_pending_start, cases_instituted, cases_disposed, hearings_listed, hearings_adjourned, cases_pending_over_3y, cases_pending_over_5y = counts
    if any(v is not None and (not math.isfinite(float(v)) or v < 0) for v in counts):
        raise ValueError("Counts cannot be negative")
    if any(v is not None and int(v) != v for v in counts):
        raise ValueError("Counts must be whole numbers")
    end = None if any(v is None for v in counts[:3]) else cases_pending_start + cases_instituted - cases_disposed
    if end is not None and end < 0:
        raise ValueError("Disposals cannot exceed opening stock plus institutions")
    if end is not None and cases_pending_over_3y is not None and cases_pending_over_3y > end:
        raise ValueError("Over-three-year stock cannot exceed ending stock")
    if (cases_pending_over_3y is not None and cases_pending_over_5y is not None
            and cases_pending_over_5y > cases_pending_over_3y):
        raise ValueError("Over-five-year stock cannot exceed over-three-year stock")
    if (hearings_listed is not None and hearings_adjourned is not None
            and hearings_adjourned > hearings_listed):
        raise ValueError("Adjourned hearings cannot exceed listed hearings")
    return {
        "cases_pending_end": {"value": end, "method": "Opening pending + instituted − disposed"},
        "pendency_rate": _ratio(end, cases_pending_start, "Ending pending ÷ opening pending"),
        "clearance_rate": _ratio(cases_disposed, cases_instituted, "Disposed ÷ instituted"),
        "adjournment_rate": _ratio(hearings_adjourned, hearings_listed, "Adjourned ÷ listed"),
        "share_pending_over_3y": _ratio(cases_pending_over_3y, end, "Pending over 3 years ÷ ending pending"),
        "share_pending_over_5y": _ratio(cases_pending_over_5y, end, "Pending over 5 years ÷ ending pending"),
    }


def month_successor(ym: str, offset: int) -> str:
    y, m = map(int, ym.split("-"))
    absolute = y * 12 + m - 1 + offset
    return f"{absolute // 12:04d}-{absolute % 12 + 1:02d}"


def _metric_rows(df: pd.DataFrame, dimensions: list[str], rolling: bool = False) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    if df.empty:
        return output
    for keys, group in df.groupby(dimensions, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        base = dict(zip(dimensions, keys))
        group = group.sort_values("month")
        by_month = {r.month: r for r in group.itertuples(index=False)}
        months = sorted(by_month)
        for ym in months:
            row = by_month[ym]
            vals = dict(cases_pending_start=int(row.cases_pending_start),
                        cases_instituted=int(row.cases_instituted), cases_disposed=int(row.cases_disposed),
                        hearings_listed=int(row.hearings_listed), hearings_adjourned=int(row.hearings_adjourned),
                        cases_pending_over_3y=int(row.cases_pending_over_3y),
                        cases_pending_over_5y=int(row.cases_pending_over_5y))
            metrics = calculate_metrics(**vals)
            output.append({**base, "month": ym, "period": "monthly", **vals,
                           "cases_pending_end": metrics["cases_pending_end"]["value"], "metrics": metrics})
            if rolling:
                window = [month_successor(ym, -2), month_successor(ym, -1), ym]
                if not all(m in by_month for m in window):
                    blank = {k: {"value": None, "method": "Calendar rolling 3-month ratio of aggregate totals; incomplete window (all 3 calendar months required)"}
                             for k in ("cases_pending_end", "pendency_rate", "clearance_rate", "adjournment_rate", "share_pending_over_3y", "share_pending_over_5y")}
                    output.append({**base, "month": ym, "period": "rolling_3m", "metrics": blank,
                                   "method_note": "Incomplete calendar window; no interpolation"})
                    continue
                window_rows = [by_month[m] for m in window]
                start, end = int(window_rows[0].cases_pending_start), int(window_rows[-1].cases_pending_end)
                instituted = sum(int(r.cases_instituted) for r in window_rows)
                disposed = sum(int(r.cases_disposed) for r in window_rows)
                listed = sum(int(r.hearings_listed) for r in window_rows)
                adjourned = sum(int(r.hearings_adjourned) for r in window_rows)
                age3, age5 = int(window_rows[-1].cases_pending_over_3y), int(window_rows[-1].cases_pending_over_5y)
                rmetrics = {
                    "cases_pending_end": {"value": end, "method": "Ending stock from final month; stock is not summed"},
                    "pendency_rate": _ratio(end, start, "Final month ending pending ÷ first month opening pending"),
                    "clearance_rate": _ratio(disposed, instituted, "Three-month disposed total ÷ three-month instituted total"),
                    "adjournment_rate": _ratio(adjourned, listed, "Three-month adjourned total ÷ three-month listed total"),
                    "share_pending_over_3y": _ratio(age3, end, "Final month over-three-year snapshot ÷ final month ending pending"),
                    "share_pending_over_5y": _ratio(age5, end, "Final month over-five-year snapshot ÷ final month ending pending"),
                }
                output.append({**base, "month": ym, "period": "rolling_3m", "cases_pending_start": start,
                               "cases_pending_end": end, "cases_instituted": instituted, "cases_disposed": disposed,
                               "hearings_listed": listed, "hearings_adjourned": adjourned,
                               "cases_pending_over_3y": age3, "cases_pending_over_5y": age5,
                               "metrics": rmetrics})
    return output


def build_views(data: pd.DataFrame, context: pd.DataFrame | None = None) -> dict[str, Any]:
    """Build monthly and rolling records without summing stocks across months.

    Opening stock comes from the first window month, ending stock and age-band
    snapshots come from the final month, and flow counts are summed before ratios
    are calculated. Rolling results require three calendar months and stable
    contributing source-grain coverage. Optional context joins only on the pair
    ``(state, district)`` and never changes court counts.
    """
    views = {
        "by_state": ["state"],
        "by_court_type": ["court_type"],
        "by_category": ["case_category"],
    }
    output = {}
    def build_one(name, dims, attach_context=False):
        part = data.groupby(dims + ["month"], as_index=False, dropna=False).agg({
            "cases_pending_start": "sum", "cases_instituted": "sum", "cases_disposed": "sum",
            "hearings_listed": "sum", "hearings_adjourned": "sum",
            "cases_pending_over_3y": "sum", "cases_pending_over_5y": "sum"})
        part["cases_pending_end"] = part.cases_pending_start + part.cases_instituted - part.cases_disposed
        # Age values are snapshots and must use the latest source month, not sum across months.
        records = _metric_rows(part, dims, rolling=True)
        # A calendar month can exist while contributing district/court/category cells vary.
        # Do not compare aggregate rates across windows with changing source coverage.
        for row in records:
            if row["period"] != "rolling_3m":
                continue
            window = [month_successor(row["month"], -2), month_successor(row["month"], -1), row["month"]]
            if not all(m in set(data.month) for m in window):
                continue
            subset = data
            for dim in dims:
                subset = subset[subset[dim] == row[dim]]
            contributing = []
            for month in window:
                month_rows = subset[subset.month == month]
                contributing.append(set(tuple(v) for v in month_rows[["state", "district", "court_type", "case_category"]].itertuples(index=False, name=None)))
            if not (contributing[0] == contributing[1] == contributing[2]):
                row["metrics"] = {k: {"value": None, "method": "Unavailable because contributing district/court/category coverage changes within the calendar window"}
                                  for k in ("cases_pending_end", "pendency_rate", "clearance_rate", "adjournment_rate", "share_pending_over_3y", "share_pending_over_5y")}
                row["method_note"] = "Contributing source grain changed across the three calendar months; no carry-forward or imputation"
        if attach_context and context is not None and not context.empty:
            if context.duplicated(["state", "district"]).any():
                raise ValueError("Context data contains duplicate state/district keys")
            ctx = context
            for row in records:
                found = ctx[(ctx.state == row["state"]) & (ctx.district == row["district"])]
                if len(found):
                    c = found.iloc[0]
                    row["context"] = {k: c[k] for k in ("population", "judge_strength", "budget") if k in c and pd.notna(c[k])}
                    if "population" in row.get("context", {}) and row.get("cases_pending_end") is not None:
                        pop = row["context"]["population"]
                        row["context"]["pending_per_lakh"] = {"value": (row["cases_pending_end"] / pop * 100000) if pop else None,
                                                              "method": "Ending pending ÷ population × 100,000; contextual derived value"}
                        row["context_method"] = "Derived pending per lakh = ending pending ÷ population × 100,000; context joins on state and district only"
        return records
    for name, dims in views.items():
        output[name] = build_one(name, dims)
    output["by_district"] = {
        "series": build_one("by_district_series", ["state", "district"], attach_context=True),
        "slices": build_one("by_district_slices", ["state", "district", "court_type", "case_category"]),
    }
    return output
