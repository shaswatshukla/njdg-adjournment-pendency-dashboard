"""Generate crawlable evidence pages from validated aggregate outputs; no network or new dependencies."""
from html import escape
import json
from pathlib import Path
import posixpath
import re
import unicodedata
from urllib.parse import quote
try:
    from .landing import indian_number
except ImportError:
    from landing import indian_number

BASE = 'https://justice-metrics.vercel.app'
REPO = 'https://github.com/shaswatshukla/njdg-adjournment-pendency-dashboard'
VERSION = '0.8.0'


def slug(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', value).strip('-')


class HTML(str):
    """Locally constructed markup; external strings must pass through escape first."""


def link(url, text):
    return HTML(f'<a href="{escape(url, quote=True)}">{escape(str(text))}</a>')


def cell(value):
    if isinstance(value, HTML):
        return str(value)
    if value is None:
        return 'Unavailable'
    return escape(indian_number(value) if isinstance(value, int) else str(value))


def table(headers, rows, caption):
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="'+escape(caption, quote=True)+'"><table><caption>'+escape(caption)+'</caption><thead><tr>'+''.join('<th scope="col">'+escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+cell(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def source_link(snapshot, level):
    source = snapshot['source']
    name = source['source_table_by_level'][level]
    page = source['source_pages'][name]
    return link(source['source_url']+f'#page={page}', f'{name}, PDF page {page}')


def monthly(rows):
    return table(['Court / district', 'Month', 'Category', 'Reported opening', 'Instituted', 'Disposed', 'Month-end pending', 'Clearance (derived)', 'Primary source'], [
        [r['court_label'], r['month'], r['category'], r['opening'], r['instituted'], r['disposed'], r['pending'], f"{r['clearance_rate']['value']*100:.1f}%" if r['clearance_rate']['value'] is not None else None, link(r['source']['source_url']+f"#page={r['source_page']}", f"PDF page {r['source_page']}")]
        for r in sorted(rows, key=lambda r:(r['month'], r['category']))], 'Verified monthly aggregate reports; Total is not added to Civil or Criminal')


def write_evidence(site, snapshot, periodic, crime, meta, refresh):
    """Create stable HTML URLs and metadata without inventing missing coverage or licences."""
    if not snapshot.get('available'):
        return []
    site = Path(site)
    pages = []
    date = snapshot['data_as_of']
    district_rows = [r for r in periodic['records'] if r['court_level']=='district']
    states = sorted([r for r in snapshot['records'] if r['court_level']=='district_subordinate_aggregate'], key=lambda r:r['state'])
    scopes = '<p class="alert">Historical reports, not live data. State/UT district-subordinate aggregates are not individual district observations. National direction is unavailable from a single comparable date.</p>'
    owner = {'@type':'Person', 'name':'Shaswat Shukla', 'url':'https://github.com/shaswatshukla'}

    def dataset(name, description, coverage, sources, distribution):
        return {'@context':'https://schema.org','@type':'Dataset','name':name,'description':description,'creator':owner,'temporalCoverage':coverage,'spatialCoverage':{'@type':'Place','name':'India'},'isBasedOn':sources,'distribution':{'@type':'DataDownload','contentUrl':BASE+'/'+distribution,'encodingFormat':'application/json'},'variableMeasured':(['Registered IPC cases','Registered SLL cases'] if distribution.endswith('crime.json') else ['Reported pending cases','Reported institutions','Reported disposals','Derived clearance rate'] if distribution.endswith('periodic_reports.json') else ['Reported pending cases','Reported pending over five years']), 'conditionsOfAccess':'Published aggregate facts. Source-specific reuse terms remain unverified; no commercial clearance is claimed.'}

    def page(path, title, description, body, structured=None):
        directory = path.strip('/')
        relative = lambda dest: posixpath.relpath(dest or '.', directory or '.') + ('/' if dest and not Path(dest).suffix else '')
        canonical = BASE+'/'+(directory+'/' if directory else '')
        nav = [('','Dashboard'),('states','State/UT totals'),('district-reports','District detail'),('sources','Sources'),('methodology','Methods')]
        schema = structured or {'@context':'https://schema.org','@type':'WebPage','name':title,'description':description,'author':owner}
        schema = {**schema,'url':canonical,'@id':canonical+('#dataset' if schema.get('@type')=='Dataset' else '#page')}
        schema_json = json.dumps(schema,ensure_ascii=True).replace('<', '\\u003c')
        html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)} | Justice Metrics</title><meta name="description" content="{escape(description, quote=True)}"><link rel="canonical" href="{canonical}"><meta property="og:title" content="{escape(title, quote=True)} | Justice Metrics"><meta property="og:description" content="{escape(description, quote=True)}"><meta property="og:type" content="website"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}/assets/social-card.png"><meta name="twitter:card" content="summary"><link rel="icon" type="image/svg+xml" href="{relative('favicon.svg')}"><link rel="stylesheet" href="{relative('css/styles.css')}?v={VERSION}"><script src="{relative('js/theme.js')}"></script><script type="application/ld+json">{schema_json}</script></head><body class="document-page"><a class="skip-link" href="#evidence-main">Skip to content</a><header class="document-header"><a class="document-brand" href="{relative('')}">Justice Metrics</a><nav aria-label="Evidence pages">{''.join(str(link(relative(dest), label)) for dest,label in nav)}</nav></header><main id="evidence-main" tabindex="-1"><p class="breadcrumb">{link(relative(''), 'Dashboard')} / Evidence</p><section class="page-heading"><p class="eyebrow">PUBLISHED AGGREGATE EVIDENCE</p><h1>{escape(title)}</h1><p>{escape(description)}</p></section>{body}<section class="panel"><h2>Ownership, corrections and data use</h2><p>Maintainer: <a href="https://github.com/shaswatshukla">Shaswat Shukla</a>. Independent project; not affiliated with NJDG. Not legal advice; no outcome predictions.</p><p><a href="{REPO}/issues">Report a correction</a> with the reporting period, exact figure and primary report page. Keep personal and case-level information out of submissions. Corrections require source review and validation; prior versions remain in repository history.</p><p>Code licence and source-data rights are separate. Source-specific reuse terms remain unverified; no commercial data clearance is claimed. {link(relative('sources'), 'Review source dates and limitations')}.</p></section></main><footer><span>Justice Metrics · Independent aggregate analysis</span><span>National reference date: {date}. Other datasets have separate periods.</span></footer></body></html>'''
        target = site/directory/'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding='utf-8')
        pages.append(canonical)

    def national_table(rows, caption):
        return table(['Reporting unit','Reporting level','Reporting date','Pending','Over 5 years','Primary source'], [[r['court_label'],r['court_level'].replace('_',' '),r['snapshot_date'],r['cases_pending'],r['cases_pending_over_5y'],source_link(snapshot,r['court_level'])] for r in rows],caption)

    page('states','State and UT court pendency',f'District and subordinate court aggregates for {len(states)} States/UTs, reported on {date}.',scopes+table(['State/UT','Pending','Over 5 years','Evidence'],[[r['state'],r['cases_pending'],r['cases_pending_over_5y'],link(slug(r['state'])+'/',r['state']+' source and coverage')] for r in states],'State/UT aggregates; not district rankings'))
    for row in states:
        loaded = [r for r in district_rows if r['state']==row['state']]
        identities = sorted({r['district'] for r in loaded})
        body = scopes+national_table([row], row['state']+' — dated district/subordinate aggregate')
        body += '<section class="panel"><h2>Individual district coverage</h2><p>'+('Loaded districts: '+escape(', '.join(identities))+'.' if identities else 'No verified individual district report is loaded for this State/UT. Missing coverage does not mean zero cases.')+'</p>'
        body += ''.join('<p>'+str(link('../../districts/'+slug(row['state'])+'/'+slug(d)+'/',d+' monthly evidence'))+'</p>' for d in identities)+'</section>'
        body += '<p>'+str(link('../../#state?state='+quote(row['state']), 'Open the interactive State/UT explorer'))+'</p>'
        page('states/'+slug(row['state']),row['state']+' court pendency',f"{indian_number(row['cases_pending'])} pending district/subordinate cases as of {date}; individual district coverage is stated separately.",body,dataset(row['state']+' district/subordinate pendency', 'One State/UT aggregate; not an individual district count.',date,[snapshot['source']['source_url']],'data/official_snapshot.json'))

    page('courts','Reported court categories',f"{len(snapshot['records'])} published reporting units on {date}; not complete coverage of every judicial body.",scopes+national_table(snapshot['records'],'National parliamentary snapshot — 62 reporting units'))
    hc = [r for r in snapshot['records'] if r['court_level']=='high_court']
    page('high-courts','High Court pendency',f'{len(hc)} reported High Courts on {date}. Shared-jurisdiction High Courts are counted once.',scopes+national_table(hc,'High Courts — reported stocks, not monthly flows'),dataset('High Court pending cases','Historical stocks for 25 High Courts; no case lookup or monthly national trend.',date,[snapshot['source']['source_url']],'data/official_snapshot.json'))
    sc = [r for r in snapshot['records'] if r['court_level']=='supreme_court']
    sc_monthly = [r for r in periodic['records'] if r['court_level']=='supreme_court']
    page('supreme-court','Supreme Court pendency and historical monthly reports',f'National stock dated {date}; separate monthly series January–August 2025.',scopes+national_table(sc,'Supreme Court national reference stock')+'<h2>Separate historical monthly series</h2><p>Do not join these dates to the national stock. Clearance is disposals divided by institutions; zero institutions gives unavailable. Opening stocks are not inferred. This is not a performance score.</p>'+monthly(sc_monthly),dataset('Supreme Court historical monthly reports','Civil, Criminal and Total rows remain separate. Annual report PDF page 223.', '2025-01/2025-08',[r['source_url'] for r in periodic['reports'] if r['court_level']=='supreme_court'],'data/periodic_reports.json'))
    pairs = sorted({(r['state'],r['district']) for r in district_rows})
    correction='<p class="alert">'+escape(refresh.get('periodic_check',{}).get('note','Only the stated periodic reports are loaded.'))+'</p>'
    coverage = correction+'<p class="alert">Partial coverage: '+str(len(pairs))+' individual district(s). Nationwide district coverage is incomplete. No national district rankings or trend are inferred.</p>'
    page('district-reports','Verified district reports — partial coverage','Only the districts and reporting periods listed here have loaded, validated reports.',coverage+table(['State','District','Loaded months','Evidence'],[[state,district,', '.join(sorted({r['month'] for r in district_rows if r['state']==state and r['district']==district})),link('../districts/'+slug(state)+'/'+slug(district)+'/', 'Read monthly evidence')] for state,district in pairs],'Loaded individual district reports'))
    for state,district in pairs:
        rows = [r for r in district_rows if r['state']==state and r['district']==district]
        page('districts/'+slug(state)+'/'+slug(district),district+', '+state+' — monthly court reports','Historical aggregate monthly counts for this district only. Dates and source pages remain attached to each row.',coverage+monthly(rows)+'<p>Stocks are not summed across months. Clearance is disposed/instituted, not a verdict or safety measure. A difference between two stocks alone does not establish its cause.</p>',dataset(district+' monthly court aggregates','Partial individual district coverage; not a national estimate.', min(r['month'] for r in rows)+'/'+max(r['month'] for r in rows),sorted({r['source']['source_url'] for r in rows}),'data/periodic_reports.json'))

    rows = meta.get('sources',[])
    registry = table(['Source','Reporting period','Recorded download','Access / limits'],[[r['source_name'],r['coverage_start']+' to '+r['coverage_end'],r['download_date'],HTML(str(link(r['source_url'],'Primary report'))+'<br>'+escape(r['notes'])+'<br>Rights: '+escape(r['licence']))] for r in rows],'Source registry — download dates are not reporting or refresh dates')
    page('sources','Sources, dates and coverage','Trace each dataset to a published source, reporting period, page citation and stated limitation.',scopes+correction+registry+'<section class="panel"><h2>National headline citation</h2><p>The combined pending figure sums Supreme Court and High Court stocks in '+str(source_link(snapshot,'supreme_court'))+' with State/UT district-subordinate stocks in '+str(source_link(snapshot,'district_subordinate_aggregate'))+'. These are distinct categories, not evidence of every court or tribunal.</p><h2>Verification status</h2><p>Latest recorded national attempt: '+escape(str(refresh.get('last_checked_at_utc','Unavailable')))+'; result '+escape(str(refresh.get('status','Unavailable')))+'.</p><p>'+escape(refresh.get('note','No check note available.'))+'</p><p>Build, download, source check and reporting dates mean different things. A deployment does not make historical figures current.</p><p>'+str(link('../data/meta.json','Download provenance JSON'))+' · '+str(link('../data/refresh_status.json','Download check-status JSON'))+'</p></section>')
    page('methodology','Methodology and definitions','Reported stocks, derived ratios, source granularity and the limits on comparison.', '<section class="panel"><h2>Reported pending stock</h2><p>A count at its stated date, not an annual flow. National pending adds only the three published court categories.</p><h2>Concentration (derived)</h2><p>Sum the three largest district/subordinate State/UT pending stocks, then divide by the sum for all loaded State/UT aggregates. Higher courts are excluded. This is not population-adjusted.</p><h2>Over-five-year share (derived)</h2><p>Reported cases pending over five years divided by reported pending. For combined figures, sum counts first; never average ratios. Zero denominators give unavailable.</p><h2>Monthly clearance (derived)</h2><p>Reported disposals divided by reported institutions. Zero institutions gives unavailable. Do not sum Total with Civil and Criminal components. Reported opening + institutions - disposals must reconcile where opening is supplied; no opening is inferred.</p><h2>Unavailable measures</h2><p>National monthly direction, national clearance and adjournment rates, and comprehensive individual district detail are unavailable in the national source. Missing counts are not zero.</p><h2>Crime context is separate</h2><p>Annual registered crimes are flows. Pending court cases are stocks. They are not equivalent measures or a combined score. The 2023 series is pre-BNS; post-July-2024 data needs a reviewed IPC/BNS mapping.</p><h2>Validation and corrections</h2><p>Inputs require registered sources and reviewed controls. Invalid schemas, personal-data headers, negative counts, duplicate identities and broken reconciliation are rejected. Changes pass pipeline checks before publication. No scraping, case-level data or personal records are used.</p></section>')
    page('crime','Registered crime in India — separate historical context',f"{crime['year']} IPC/SLL registered cases for {len(crime['records'])} States/UTs. Not convictions, incidence, safety scores or court backlog.", '<p class="alert">Annual registrations and pending court stocks have different meanings and dates. No causal comparison, population rate or combined score is calculated.</p>'+table(['State/UT','IPC','SLL','IPC + SLL'],[[r['state'],r['ipc'],r['sll'],r['total']] for r in crime['records']],str(crime['year'])+' registered cognizable crimes')+'<p>'+str(link(crime['source']['source_url']+'#page=3','MHA/NCRB primary table, PDF page 3'))+' · '+str(link('../#crime','Open the interactive geographic map'))+'</p><p>IPC-to-BNS transition: July 2024. This pre-transition series is not spliced to BNS counts. Source-specific reuse terms remain unverified.</p>',dataset('Registered cognizable crime, '+str(crime['year']),'Historical IPC/SLL annual registrations; distinct from court pendency.',str(crime['year']),[crime['source']['source_url']],'data/crime.json'))

    # Homepage metadata and the small coverage seed come from the same validated build.
    index = site/'index.html'
    text = index.read_text(encoding='utf-8')
    home_schema = dataset('Court pendency in India', 'Supreme Court, High Courts and State/UT district-subordinate stocks. Historical data; no national trend inferred.',date,[snapshot['source']['source_url']],'data/official_snapshot.json')
    home_schema['url']=BASE+'/'
    home_meta = '<link rel="canonical" href="'+BASE+'/"><meta property="og:title" content="Court pendency in India | Justice Metrics"><meta property="og:description" content="Dated official aggregate reports, backlog concentration and explicit coverage limits."><meta property="og:url" content="'+BASE+'/"><meta property="og:type" content="website"><meta property="og:image" content="'+BASE+'/assets/social-card.png"><meta name="twitter:card" content="summary"><script type="application/ld+json">'+json.dumps(home_schema,ensure_ascii=True).replace('<','\\u003c')+'</script>'
    seed = {'reference':{'data_as_of':date,'coverage':snapshot['coverage']},'districtCoverageRows':[dict(court_level='district',state=s,district=d,month=m) for s,d,m in sorted({(r['state'],r['district'],r['month']) for r in district_rows})]}
    for name,body in [('HOME_META',home_meta),('BOOTSTRAP','<script id="data-bootstrap" type="application/json">'+json.dumps(seed,ensure_ascii=True).replace('<','\\u003c')+'</script>')]:
        text,count = re.subn('<!-- '+name+':START -->.*?<!-- '+name+':END -->',lambda _: '<!-- '+name+':START -->'+body+'<!-- '+name+':END -->',text,flags=re.S)
        if count!=1:raise ValueError('Missing generated marker '+name)
    index.write_text(text,encoding='utf-8')
    pages.insert(0,BASE+'/')
    (site/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(url)+'</loc></url>' for url in pages)+'</urlset>',encoding='utf-8')
    (site/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+BASE+'/sitemap.xml\n',encoding='utf-8')
    return pages
