import csv
import json
import tempfile
import unittest
from pathlib import Path
from pipeline.periodic import validate_periodic


class PeriodicTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[2]
        self.controls=json.loads((self.root/'pipeline/periodic_controls.json').read_text(encoding='utf-8'))
        self.file='periodic/kokrajhar_2026_08.csv'
        self.control=self.controls[self.file]
        with (self.root/'pipeline/sources.csv').open(encoding='utf-8') as f:
            self.sources={r['file_name']:r for r in csv.DictReader(f)}

    def test_district_monthly_totals_and_clearance(self):
        rows=validate_periodic(self.root/'pipeline/raw'/self.file,self.sources[self.file],self.control)
        total=next(r for r in rows if r['category']=='Total')
        self.assertEqual(total['pending'],5252)
        self.assertEqual(total['opening']+total['instituted']-total['disposed'],total['pending'])
        self.assertAlmostEqual(total['clearance_rate']['value'],291/405)
        self.assertIsNone(total['adjournment_rate']['value'])

    def test_supreme_court_months_and_unreported_opening(self):
        f='periodic/supreme_court_2025.csv'
        rows=validate_periodic(self.root/'pipeline/raw'/f,self.sources[f],self.controls[f])
        self.assertEqual(len(rows),24)
        self.assertTrue(all(r['opening'] is None and r['pendency_rate']['value'] is None for r in rows))
        total=[r for r in rows if r['category']=='Total']
        self.assertEqual(sum(r['instituted'] for r in total),49671)
        self.assertEqual(total[-1]['pending'],88181)

    def modify(self,mutation):
        with (self.root/'pipeline/raw'/self.file).open() as f:rows=list(csv.DictReader(f))
        mutation(rows)
        with tempfile.TemporaryDirectory(dir=self.root) as d:
            p=Path(d)/'report.csv'
            with p.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
            with self.assertRaises(ValueError):validate_periodic(p,self.sources[self.file],self.control)

    def test_negative_refused(self):self.modify(lambda rows:rows[0].update(instituted='-1'))
    def test_missing_required_count_refused(self):self.modify(lambda rows:rows[0].update(pending=''))
    def test_wrong_identity_refused(self):self.modify(lambda rows:rows[0].update(district='Lucknow'))
    def test_wrong_month_refused(self):self.modify(lambda rows:rows[0].update(month='2026-09'))
    def test_opening_reconciliation_refused(self):self.modify(lambda rows:rows[0].update(opening='2505'))
    def test_personal_header_refused(self):self.modify(lambda rows:[r.update(party='refused') for r in rows])
    def test_zero_denominators_return_none(self):
        with (self.root/'pipeline/raw'/self.file).open() as f:rows=list(csv.DictReader(f))
        for r in rows:
            for k in ['opening','instituted','disposed','pending']:r[k]='0'
        control={**self.control,'control_totals':{'instituted':0,'disposed':0,'last_pending':0}}
        with tempfile.TemporaryDirectory(dir=self.root) as d:
            p=Path(d)/'report.csv'
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
            result=validate_periodic(p,self.sources[self.file],control)
        self.assertTrue(all(r['clearance_rate']['value'] is None and r['pendency_rate']['value'] is None for r in result))
