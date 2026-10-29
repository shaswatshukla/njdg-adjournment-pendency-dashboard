import csv
import json
import tempfile
import unittest
from pathlib import Path
from pipeline.research import load_crime, archive_snapshot, CRIME_FILE, CRIME_URL


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]
        self.path = self.root / 'pipeline/raw' / CRIME_FILE
        self.controls = json.loads((self.root / 'pipeline/official_snapshot_controls.json').read_text())
        self.source = {'source_url': CRIME_URL}
        self.states = self.controls['expected_state_ut_aggregate_labels']

    def test_crime_controls_and_all_36_states(self):
        data = load_crime(self.path,self.source,self.states)
        self.assertEqual(len(data['records']),36)
        self.assertEqual(data['totals']['total'],6241569)
        self.assertEqual(data['totals']['ipc'],3763102)
        self.assertEqual(data['totals']['sll'],2478467)

    def modified(self, mutate):
        with self.path.open(newline='') as f:
            rows=list(csv.DictReader(f))
        mutate(rows)
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            path=Path(directory)/'crime.csv'
            with path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
            with self.assertRaises(ValueError):
                load_crime(path,self.source,self.states)

    def test_crime_negative_refused(self):
        self.modified(lambda rows:rows[0].update(ipc='-1'))

    def test_crime_missing_refused(self):
        self.modified(lambda rows:rows[0].update(total=''))

    def test_crime_row_control_refused(self):
        self.modified(lambda rows:rows[0].update(total='1'))

    def test_crime_national_control_refused(self):
        self.modified(lambda rows:rows[0].update(ipc=str(int(rows[0]['ipc'])+1),total=str(int(rows[0]['total'])+1)))

    def test_crime_duplicate_state_refused(self):
        self.modified(lambda rows:rows[0].update(state=rows[1]['state']))

    def test_bns_year_refused(self):
        self.modified(lambda rows:rows[0].update(year='2024'))

    def test_personal_column_refused_before_data(self):
        self.modified(lambda rows:[r.update(party='do not ingest') for r in rows])

    def test_wrong_source_refused(self):
        with self.assertRaises(ValueError):
            load_crime(self.path,{'source_url':'https://example.org'},self.states)

    def test_archive_preserves_dates_and_blocks_silent_revision(self):
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            a={'data_as_of':'2026-03-13','source':{'csv_sha256':'one'},'records':[], 'coverage':{'published_reporting_units':0}}
            self.assertEqual(len(archive_snapshot(directory,a)['snapshots']),1)
            self.assertEqual(len(archive_snapshot(directory,a)['snapshots']),1)
            a['source']['csv_sha256']='changed'
            with self.assertRaises(ValueError):archive_snapshot(directory,a)
            a['data_as_of']='2027-01-01'
            self.assertEqual(len(archive_snapshot(directory,a)['snapshots']),2)
