"""Run the data build and verify the complete static JSON contract."""
from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED = ("meta.json", "official_snapshot.json", "refresh_status.json",
            "snapshot_archive.json", "crime.json", "periodic_reports.json")


def check_json(data_dir: Path) -> None:
    """Require and parse all JSON contracts before a build is considered successful."""
    for name in EXPECTED:
        path = data_dir / name
        if not path.is_file():
            raise ValueError(f"Smoke check failed: missing site/data/{name}")
        json.loads(path.read_text(encoding="utf-8"))
    for forbidden in ('summary.json', 'by_state.json', 'by_district.json', 'by_court_type.json', 'by_category.json'):
        if (data_dir / forbidden).exists():
            raise ValueError(f'Synthetic fixture output must not be published: {forbidden}')


def main() -> int:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    from pipeline.build import BuildError, build
    result = build()
    data_dir = ROOT / "site" / "data"
    check_json(data_dir)
    official = json.loads((data_dir / "official_snapshot.json").read_text(encoding="utf-8"))
    official_label = f"{len(official['records'])} official reporting units" if official.get("available") else "no official snapshot"
    print(f"Smoke check passed: {len(EXPECTED)} JSON files parsed; {result['records_loaded']} offline fixture rows; {official_label}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc))
        raise SystemExit(1)
