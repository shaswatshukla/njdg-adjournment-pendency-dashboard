import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree
from pipeline.pages import write_evidence, slug


ROOT=Path(__file__).resolve().parents[2]


class PageParser(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.tags=[]; self.feed(text)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag,dict(attrs)))


class EvidencePagesTests(unittest.TestCase):
    def test_published_pages_have_real_links_one_heading_and_machine_metadata(self):
        site=ROOT/'site'
        pages=list(site.rglob('index.html'))
        self.assertGreaterEqual(len(pages),46)
        for page in pages:
            text=page.read_text(encoding='utf-8');parsed=PageParser(text)
            self.assertEqual(sum(tag=='h1' for tag,attrs in parsed.tags),1,str(page))
            self.assertTrue(any(tag=='link' and a.get('rel')=='canonical' for tag,a in parsed.tags),str(page))
            self.assertTrue(any(tag=='meta' and a.get('name')=='description' for tag,a in parsed.tags),str(page))
            for tag,attrs in parsed.tags:
                address=attrs.get('src') if tag=='script' else attrs.get('href') if tag in ('a','link') else None
                if not address:continue
                url=urlsplit(address)
                if url.scheme or url.netloc or not url.path:continue
                target=(page.parent/unquote(url.path)).resolve()
                self.assertTrue(target.is_relative_to(site.resolve()),address)
                if target.is_dir():target=target/'index.html'
                self.assertTrue(target.is_file(),f'{page}: {address}')

    def test_sitemap_contains_only_real_evidence_pages(self):
        sitemap=ElementTree.parse(ROOT/'site/sitemap.xml')
        urls=[node.text for node in sitemap.findall('.//{*}loc')]
        self.assertEqual(len(urls),len(set(urls)))
        self.assertTrue(all('#' not in u for u in urls))
        for address in urls:
            self.assertTrue((ROOT/'site'/urlsplit(address).path.strip('/')/'index.html').is_file())

    def test_dataset_jsonld_does_not_invent_licences_or_crime_variables(self):
        import re
        for path in ['states/uttar-pradesh','crime','supreme-court']:
            text=(ROOT/'site'/path/'index.html').read_text(encoding='utf-8')
            data=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',text,re.S)[1])
            self.assertEqual(data['@type'],'Dataset');self.assertNotIn('license',data)
            self.assertIn('isBasedOn',data);self.assertIn('temporalCoverage',data)
            if path=='crime':self.assertEqual(data['variableMeasured'],['Registered IPC cases','Registered SLL cases'])

    def test_security_and_local_dependency_configuration(self):
        config=json.loads((ROOT/'site/vercel.json').read_text())
        headers={h['key']:h['value'] for h in config['headers'][0]['headers']}
        self.assertIn("script-src 'self';",headers['Content-Security-Policy'])
        self.assertNotIn('unsafe-eval',headers['Content-Security-Policy'])
        self.assertEqual(headers['X-Content-Type-Options'],'nosniff')
        parser=PageParser((ROOT/'site/index.html').read_text(encoding='utf-8'))
        executable=[a for tag,a in parser.tags if tag=='script' and a.get('type') not in ('application/json','application/ld+json')]
        self.assertTrue(all(a.get('src') and not urlsplit(a['src']).scheme for a in executable))

    def test_withdrawn_district_figures_never_reach_public_reports(self):
        data=json.loads((ROOT/'site/data/periodic_reports.json').read_text(encoding='utf-8'))
        rows=[r for r in data['records'] if r['court_level']=='district' and r['category']=='Total']
        self.assertEqual([(r['month'],r['pending']) for r in rows],[('2026-07',5138),('2026-08',5252)])
        self.assertEqual(rows[0]['pending'],rows[1]['opening'])
        self.assertTrue(all('excludes JJB' in r['court_label'] for r in rows))
        self.assertNotIn('periodic/kokrajhar_2026_09.csv',(ROOT/'pipeline/sources.csv').read_text(encoding='utf-8'))

    def test_state_slug(self):
        self.assertEqual(slug('Dadra and Nagar Haveli and Daman and Diu'),'dadra-and-nagar-haveli-and-daman-and-diu')

    def test_map_boundary_and_body_contrast_pairs(self):
        def luminance(value):
            channels=[int(value[i:i+2],16)/255 for i in (1,3,5)]
            linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in channels]
            return sum(x*y for x,y in zip(linear,[.2126,.7152,.0722]))
        def contrast(a,b):
            lo,hi=sorted([luminance(a),luminance(b)])
            return (hi+.05)/(lo+.05)
        for fill in ['#e5f4f1','#b1dcd4','#75b8ab']:
            self.assertGreaterEqual(contrast('#33454d',fill),3)
        for fill in ['#377e71','#174c43']:
            self.assertGreaterEqual(contrast('#e5f4f1',fill),3)
        self.assertGreaterEqual(contrast('#62717b','#ffffff'),4.5)
        self.assertGreaterEqual(contrast('#acbec9','#172a36'),4.5)
