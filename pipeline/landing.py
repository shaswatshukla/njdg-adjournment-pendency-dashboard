"""Publish an honest, dated landing snapshot before browser JavaScript or JSON loads."""
import re
from html import escape
from pathlib import Path


def indian_number(value: int) -> str:
    text = str(value)
    if len(text) <= 3:
        return text
    prefix, suffix = text[:-3], text[-3:]
    parts = []
    while prefix:
        parts.insert(0, prefix[-2:])
        prefix = prefix[:-2]
    return ','.join(parts + [suffix])


def write_landing(index: Path, snapshot: dict, periodic: dict) -> None:
    """Replace only the generated fallback; keep fixture-only builds outside the site untouched."""
    if not index.exists():
        return
    text = index.read_text(encoding='utf-8')
    if not snapshot.get('available'):
        body = '<h1>Court pendency</h1><p>Official data unavailable. No replacement figures are shown.</p>'
    else:
        rows = [r for r in snapshot['records'] if r['court_level'] == 'district_subordinate_aggregate']
        top = sorted(rows, key=lambda r: r['cases_pending'], reverse=True)[:3]
        denominator = sum(r['cases_pending'] for r in rows)
        share = f"{sum(r['cases_pending'] for r in top) / denominator:.1%}" if denominator else 'Unavailable'
        districts = sorted({f"{r['district']}, {r['state']}" for r in periodic.get('records', []) if r['court_level'] == 'district'})
        total = snapshot['reported_categories_combined']['cases_pending']
        body = f'''<section class="page-heading"><p class="eyebrow">INDIA / PUBLISHED COURT REPORTS</p><h1>Court pendency in India</h1><p>Reporting date: {escape(snapshot['data_as_of'])}. Historical figures, not a live feed.</p></section>
<section class="answer-grid" aria-label="Three questions about pendency">
<article class="panel answer-card"><h2>How many cases are pending?</h2><strong>{total / 10000000:.2f} Cr</strong><p>{indian_number(total)} across the three published court categories.</p></article>
<article class="panel answer-card"><h2>Where is it concentrated?</h2><strong>{share}</strong><p>{escape(', '.join(r['state'] for r in top))} hold this share of district/subordinate pending cases. Higher courts are excluded from this denominator.</p></article>
<article class="panel answer-card"><h2>Is the backlog improving?</h2><strong class="answer-text">National trend unavailable</strong><p>One nationwide reporting date cannot establish a direction. A separate Supreme Court historical series is available on its evidence page.</p></article></section>
<section class="panel"><h2>Coverage before comparison</h2><p>{snapshot['coverage']['high_court_count']} High Courts; Supreme Court; {len(rows)} State/UT district/subordinate aggregates. Loaded individual districts: {escape('; '.join(districts) or 'None')}. Nationwide district coverage is incomplete.</p><p><a href="{escape(snapshot['source']['source_url'], quote=True)}#page=53">Annex I, PDF page 53: Supreme Court and High Courts</a> and <a href="{escape(snapshot['source']['source_url'], quote=True)}#page=54">Annex II, PDF page 54: State/UT aggregates</a> · <a href="states/">Explore State/UT evidence</a> · <a href="supreme-court/">Supreme Court historical reports</a> · <a href="sources/">Source dates and coverage</a> · <a href="data/official_snapshot.json">Download the published snapshot JSON</a></p><p>This dated summary remains available if scripts or data requests fail. Interactive tables and charts require JavaScript.</p></section>'''
    text, count = re.subn(r'<!-- LANDING:START -->.*?<!-- LANDING:END -->', lambda _: '<!-- LANDING:START -->' + body + '<!-- LANDING:END -->', text, flags=re.S)
    if count != 1:
        raise ValueError('Expected exactly one generated landing region')
    index.write_text(text, encoding='utf-8')
