import json
from pathlib import Path
from tempfile import TemporaryDirectory
from pipeline.landing import write_landing, indian_number


def test_published_fallback_tracks_source_without_javascript():
    root = Path(__file__).resolve().parents[2]
    snapshot = json.loads((root / 'site/data/official_snapshot.json').read_text(encoding='utf-8'))
    periodic = json.loads((root / 'site/data/periodic_reports.json').read_text(encoding='utf-8'))
    with TemporaryDirectory() as folder:
        index = Path(folder) / 'index.html'
        index.write_text('before<!-- LANDING:START -->old<!-- LANDING:END -->after', encoding='utf-8')
        write_landing(index, snapshot, periodic)
        text = index.read_text(encoding='utf-8')
        assert indian_number(snapshot['reported_categories_combined']['cases_pending']) in text
        assert snapshot['data_as_of'] in text
        assert 'National trend unavailable' in text
        assert 'Kokrajhar' in text and 'incomplete' in text
        assert text.startswith('before') and text.endswith('after')
        assert 'old<!--' not in text


def test_indian_grouping():
    assert indian_number(56450345) == '5,64,50,345'
    assert indian_number(0) == '0'
    assert indian_number(1000) == '1,000'
