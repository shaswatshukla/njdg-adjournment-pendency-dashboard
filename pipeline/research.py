"""Validated research artifacts. Crime counts are never joined to court stocks."""
import csv
import json
import re
from pathlib import Path

CRIME_FILE = 'crime/registered_crime_2023.csv'
CRIME_URL = 'https://sansad.in/getFile/annex/269/AU407_UbEvYl.pdf?source=pqars'


def load_crime(path, source, expected_states):
    """Validate the manually transcribed Annexure I against published national controls."""
    with Path(path).open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        if any(re.search(r'name|phone|aadhaar|address|party|accused', c, re.I) for c in reader.fieldnames or []):
            raise ValueError('Personal-data columns refused in crime input')
        if set(reader.fieldnames or []) != {'state', 'year', 'ipc', 'sll', 'total'}:
            raise ValueError('Crime input requires state, year, ipc, sll, total only')
        records = list(reader)
    if source['source_url'] != CRIME_URL:
        raise ValueError('Crime provenance does not match verified parliamentary source')
    if len(records) != 36 or {r['state'] for r in records} != set(expected_states):
        raise ValueError('Crime input must contain exactly the 36 unique States/UTs')
    for row in records:
        for key in ('year', 'ipc', 'sll', 'total'):
            if not re.fullmatch(r'\d+', row[key]):
                raise ValueError('Crime values must be nonnegative integers')
            row[key] = int(row[key])
        if row['year'] != 2023 or row['ipc'] + row['sll'] != row['total']:
            raise ValueError('Crime year or IPC+SLL row reconciliation failed')
    totals = {k: sum(r[k] for r in records) for k in ('ipc', 'sll', 'total')}
    if totals != {'ipc': 3763102, 'sll': 2478467, 'total': 6241569}:
        raise ValueError('Crime national control totals do not reconcile')
    return {'year': 2023, 'records': records, 'totals': totals, 'source': source,
            'source_page': 3, 'table': 'Annexure I', 'law_regime': 'IPC (pre-BNS)',
            'method': 'Published registered cognizable cases; total = IPC + SLL. Counts, not population rates.',
            'limitations': ['Registered cases are not the true incidence of crime, convictions, or a safety score.',
                            'Reporting and policing practices differ across States/UTs.',
                            'Annual 2023 crime flows must not be compared as equivalent to 2026 pending court stocks.',
                            'Source commercial reuse terms are unverified.']}


def archive_snapshot(directory, snapshot):
    """Preserve verified full snapshots; refuse silent revisions to the same reporting date."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (snapshot['data_as_of'] + '.json')
    if path.exists():
        previous = json.loads(path.read_text(encoding='utf-8'))
        if previous['source']['csv_sha256'] != snapshot['source']['csv_sha256']:
            raise ValueError('Same-date source revision: review and update the archived snapshot explicitly')
    else:
        # Preserve the original reporting-date artifact, including its byte representation.
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    snapshots = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(directory.glob('????-??-??.json'))]
    for item in snapshots:
        if len(item['records']) != item['coverage']['published_reporting_units']:
            raise ValueError('Archived snapshot coverage mismatch')
    return {'snapshots': snapshots, 'note': 'Only verified reporting dates are archived; no interpolated monthly observations.'}
