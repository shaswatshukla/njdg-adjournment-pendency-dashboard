import json
import re
import unittest
from pathlib import Path
from pipeline.build_map import simplify


class MapAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.asset=json.loads((cls.root/'site/assets/maps/india-states.json').read_text(encoding='utf-8'))
        cls.expected=set(json.loads((cls.root/'pipeline/official_snapshot_controls.json').read_text())['expected_state_ut_aggregate_labels'])

    def test_all_36_names_join_without_missing_or_duplicate_regions(self):
        names=[f['state'] for f in self.asset['features']]
        self.assertEqual(len(names),36)
        self.assertEqual(len(set(names)),36)
        self.assertEqual(set(names),self.expected)
        self.assertEqual(len({f['lgd_code'] for f in self.asset['features']}),36)

    def test_paths_have_only_svg_geometry_and_labels_fit_view(self):
        for feature in self.asset['features']:
            self.assertRegex(feature['path'],r'^[-\d.,MLZ]+$')
            self.assertTrue(feature['path'].endswith('Z'))
            x,y=feature['label'];self.assertTrue(0<=x<=800 and 0<=y<=880)

    def test_boundary_provenance_and_six_small_ut_targets(self):
        source=self.asset['source']
        self.assertEqual(source['url'],'https://bharatlas.com/api/dl/admin/states/LGD_States.geojson')
        self.assertRegex(source['source_sha256'],r'^[a-f0-9]{64}$')
        self.assertIn('CC-BY-4.0',source['licence'])
        self.assertEqual(sum(f['marker'] for f in self.asset['features']),6)

    def test_simplification_retains_tiny_rings_and_endpoints(self):
        tiny=[[0,0],[.01,0],[.01,.01],[0,0]]
        self.assertEqual(simplify(tiny),tiny)
        line=[[0,0],[1,0],[2,0],[3,0],[4,0]]
        self.assertEqual(simplify(line),[[0,0],[4,0]])

    def test_no_synthetic_interface_or_requests(self):
        html=(self.root/'site/index.html').read_text(encoding='utf-8')
        app=(self.root/'site/js/app.js').read_text(encoding='utf-8')
        self.assertNotIn('dataset-mode',html)
        self.assertNotIn('demo-view',html)
        self.assertNotIn('getJSON(\'summary\')',app)
        self.assertNotIn('Synthetic - FOR DEMO',html)
