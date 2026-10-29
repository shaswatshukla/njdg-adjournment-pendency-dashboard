import { researchRoutes, renderResearch, addResearchActions } from './research.js?v=0.4.0';
import { reportRoutes, courtLinks } from './court-reports.js?v=0.4.0';
const n = value => {
  if (value == null) return '-';
  const v = Number(value);
  if (Math.abs(v) >= 10000000) return `${(v / 10000000).toFixed(1)} Cr`;
  if (Math.abs(v) >= 100000) return `${(v / 100000).toFixed(1)} L`;
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(v);
};
const pct = value => value == null ? '-' : `${(Number(value) * 100).toFixed(1)}%`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' })[ch]);
const charts = new Map();
const levelNames = { supreme_court:'Supreme Court', high_court:'High Courts', district_subordinate_aggregate:'State/UT district/subordinate aggregates' };

function dateLabel(value) {
  if (!value) return 'Unknown';
  const date = new Date(value.includes('T') ? value : `${value}T00:00:00Z`);
  return Number.isNaN(date.valueOf()) ? String(value) : new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(date);
}

export function updateOfficialModeStatus(snapshot, refresh, element) {
  if (!snapshot || !element) return;
  if (!refresh) {
    element.textContent = `Historical snapshot · Data as of ${dateLabel(snapshot.data_as_of)} · Source-check status unavailable.`;
    element.className = 'mode-status warning';
    return;
  }
  const checked = dateLabel(refresh.last_checked_at_utc);
  const dataDate = dateLabel(snapshot.data_as_of);
  let message = `Historical snapshot · Data as of ${dataDate} · Source checked ${checked} · Daily verification scheduled`;
  if (refresh.status === 'needs_review') message = `Verification needs review · Last verified data as of ${dataDate} · Source checked ${checked} · Review needed`;
  if (refresh.status === 'error') message = `Source verification error · Last verified data as of ${dataDate} · Source checked ${checked} · Action needed`;
  if (refresh.status === 'no_change') message = `No newer verified table · Data as of ${dataDate} · Source checked ${checked} · Daily verification scheduled`;
  if (refresh.status === 'updated') message = `Verified snapshot · Data as of ${dataDate} · Source checked ${checked} · Daily verification scheduled`;
  element.textContent = message;
  element.className = `mode-status ${['needs_review','error'].includes(refresh.status) ? 'warning' : ''}`;
}

function officialMeta(snapshot, refresh) {
  return `<p class="official-meta">Data as of ${dateLabel(snapshot.data_as_of)} · Source checked ${dateLabel(refresh?.last_checked_at_utc)} · ${n(snapshot.coverage.published_reporting_units)} published reporting units</p>`;
}

function markup(route, snapshot, refresh) {
  const source = esc(snapshot.source.source_url);
  const sourceTitle = esc(snapshot.source.title);
  const sourceTables = snapshot.source.source_table_by_level;
  const sourcePages = snapshot.source.source_pages;
  const meta = officialMeta(snapshot, refresh);
  const coverage = snapshot.coverage;
  const status = '<div class="data-status" role="status" aria-live="polite">Loading official snapshot...</div>';
  if (route === 'overview') return `<section class="page-heading"><p class="eyebrow">OFFICIAL SNAPSHOT · PARLIAMENTARY REPLY</p><h1>Reported court pendency</h1><p>A dated public snapshot from ${sourceTitle}.</p>${meta}</section><div class="alert alert-strong"><strong>Historical snapshot, not live data.</strong> District and subordinate figures are state/UT aggregates, not district-level figures. Tribunal coverage is not stated.</div>${status}<section class="kpi-grid" aria-label="Reported snapshot metrics"><article class="kpi"><p>Pending across reported categories</p><strong id="official-pending">-</strong><small>${coverage.supreme_court_count} Supreme Court · ${coverage.high_court_count} High Courts · ${coverage.state_ut_aggregate_count} state/UT aggregates</small></article><article class="kpi"><p>Clearance rate</p><strong id="official-clearance">Unavailable</strong><small>Institutions and disposals are not reported</small></article><article class="kpi"><p>Adjournment rate</p><strong id="official-adjournment">Unavailable</strong><small>Hearings are not reported</small></article><article class="kpi"><p>Long-pendency share (over 5 years)</p><strong id="official-share">-</strong><small>Derived as over-five-year count ÷ pending</small></article></section><section class="chart-grid"><article class="panel chart-panel"><div class="panel-heading"><div><p class="eyebrow">REPORTED STOCK</p><h2>Pending by state/UT aggregate</h2></div><span class="unit">Cases</span></div><div class="chart-wrap official-bars"><canvas id="official-state-bars" role="img" aria-label="Reported pending cases by state or union territory aggregate"></canvas></div><p class="chart-method">Each bar is the published district and subordinate court aggregate for one state/UT. It is not a district or individual court count.</p></article><article class="panel"><p class="eyebrow">PUBLISHED LEVEL TOTALS</p><h2>Court categories reported</h2><div class="table-scroll"><table><thead><tr><th>Reporting category</th><th class="numeric">Units</th><th class="numeric">Pending</th><th class="numeric">Over 5 years</th></tr></thead><tbody id="official-level-totals"></tbody></table></div><p class="chart-method">The combined figure adds the three published categories. It does not establish complete coverage of every judicial body.</p></article></section><section class="panel"><p class="eyebrow">LIMITS</p><h2>Only the reported snapshot is shown.</h2><p>No institution, disposal, hearing, adjournment, opening-stock, over-three-year, or monthly series is available in these tables. The dashboard leaves those measures unavailable.</p><a class="text-link" href="#methodology">Read the source and metric notes</a></section>`;
  if (route === 'state') return `<p class="breadcrumb"><a href="#overview">Overview</a> / State explorer</p><section class="page-heading"><p class="eyebrow">OFFICIAL SNAPSHOT · STATE/UT</p><h1>State and UT aggregates</h1><p>Explore the published district and subordinate court aggregate for each state/UT.</p>${meta}</section><div class="alert"><strong>Granularity limit.</strong> This source does not provide district rows or monthly trends for these totals.</div>${status}<section class="panel controls"><label for="official-state-select">State or union territory<select id="official-state-select"></select></label><span id="official-state-coverage" class="unit"></span></section><section class="kpi-grid"><article class="kpi"><p>Reported pending</p><strong id="official-state-pending">-</strong><small>District/subordinate aggregate</small></article><article class="kpi"><p>Pending over 5 years</p><strong id="official-state-over5">-</strong><small>Reported nested age count</small></article><article class="kpi"><p>Over-5-year share</p><strong id="official-state-share">-</strong><small>Derived from reported counts</small></article><article class="kpi"><p>Monthly trends</p><strong>Unavailable</strong><small>One dated snapshot only</small></article></section><section class="panel table-panel"><div class="table-heading"><div><p class="eyebrow">SELECTED REPORTING UNIT</p><h2>District and subordinate courts</h2></div></div><div class="table-scroll"><table><thead><tr><th>Reporting unit</th><th>State/UT</th><th>Snapshot</th><th class="numeric">Pending</th><th class="numeric">Over 5 years</th><th class="numeric">Share over 5 years</th></tr></thead><tbody id="official-state-row"></tbody></table></div></section><p class="method-note">A state/UT aggregate does not support district rankings. The source does not report case-flow ratios.</p>`;
  if (route === 'district') return `<p class="breadcrumb"><a href="#overview">Overview</a> / Court coverage</p><section class="page-heading"><p class="eyebrow">OFFICIAL SNAPSHOT · REPORTING UNITS</p><h1>Court coverage</h1><p>Browse the ${coverage.published_reporting_units} reporting units in the parliamentary tables and export the filtered view.</p>${meta}</section><div class="alert"><strong>Level labels show source granularity.</strong> “State/UT aggregate” represents district and subordinate courts collectively; it is not one court.</div>${status}<section class="panel filter-panel"><label>Reporting level<select id="official-level-filter"><option value="">All levels</option><option value="supreme_court">Supreme Court</option><option value="high_court">High Courts</option><option value="district_subordinate_aggregate">State/UT aggregate</option></select></label><label>State/UT<select id="official-state-filter"><option value="">All states/UTs</option></select></label><label>Sort by<select id="official-sort"><option value="cases_pending">Pending, high to low</option><option value="cases_pending_over_5y">Over 5 years, high to low</option><option value="court_label">Reporting unit A-Z</option></select></label><button class="button-secondary" id="official-download" type="button">Download filtered CSV</button></section><section class="panel table-panel"><div class="table-heading"><div><p class="eyebrow">SOURCE SNAPSHOT</p><h2>Published reporting units</h2></div><span id="official-row-count" class="unit"></span></div><div class="table-scroll"><table><thead><tr><th>Reporting unit</th><th>Reporting level</th><th>State/UT</th><th>Snapshot date</th><th class="numeric">Pending</th><th class="numeric">Over 5 years</th><th class="numeric">Share over 5 years</th></tr></thead><tbody id="official-rows"></tbody></table></div></section>`;
  if (route === 'methodology') return `<p class="breadcrumb"><a href="#overview">Overview</a> / Methodology</p><section class="page-heading"><p class="eyebrow">OFFICIAL SNAPSHOT · METHODS</p><h1>What the source reports</h1><p>Counts are presented at their published reporting level; unreported measures remain unavailable.</p>${meta}</section><div class="alert alert-strong"><strong>Historical, cross-sectional data.</strong> This is not a live feed and cannot support monthly trends or case-flow rates.</div>${status}<section class="formula-grid"><article class="panel formula"><p class="eyebrow">REPORTED STOCK</p><h2>Pending cases</h2><code>Source reported count</code><p>The source snapshot reports the pending stock as of ${dateLabel(snapshot.data_as_of)}.</p></article><article class="panel formula"><p class="eyebrow">REPORTED AGE COUNT</p><h2>Pending over 5 years</h2><code>Source reported count</code><p>A nested age-band count, as published by reporting category.</p></article><article class="panel formula"><p class="eyebrow">DERIVED RATIO</p><h2>Over-5-year share</h2><code>Reported pending over 5 years ÷ reported pending</code><p>For combined totals, both counts are summed first; the ratio is not an average of category shares.</p></article><article class="panel formula"><p class="eyebrow">UNAVAILABLE</p><h2>Case-flow rates</h2><code>No numerator or denominator supplied</code><p>Institution, disposal, hearing, opening-stock, over-three-year, and monthly fields are not reported.</p></article></section><section class="panel"><p class="eyebrow">PRIMARY SOURCE</p><h2>${sourceTitle}</h2><p>Answered ${dateLabel(snapshot.source.answer_date)}; data as of ${dateLabel(snapshot.data_as_of)}.</p><ul><li><a href="${source}#page=${sourcePages[sourceTables.supreme_court]}" target="_blank" rel="noopener">${esc(sourceTables.supreme_court)}, PDF page ${sourcePages[sourceTables.supreme_court]}: Supreme Court and High Courts</a></li><li><a href="${source}#page=${sourcePages[sourceTables.district_subordinate_aggregate]}" target="_blank" rel="noopener">${esc(sourceTables.district_subordinate_aggregate)}, PDF page ${sourcePages[sourceTables.district_subordinate_aggregate]}: state/UT district and subordinate court aggregates</a></li></ul><p>Reuse/commercial terms have not been verified. The repository MIT license covers project code, not this source data.</p><p class="method-note"><strong>Refresh note:</strong> ${esc(refresh?.note || 'No refresh note is available.')}</p></section>`;
  return `<section class="page-heading"><p class="eyebrow">ABOUT THIS DATASET</p><h1>A verified historical source, with limits.</h1><p>The source and its coverage are shown for review. The data is not current/live and is not cleared for commercial reuse.</p>${meta}</section><div class="alert alert-strong"><strong>Commercial access is not verified.</strong> Reuse terms for the source data have not been confirmed. Do not assume the software MIT license grants data rights.</div>${status}<section class="two-column"><article class="panel"><p class="eyebrow">COVERAGE</p><h2>What is included</h2><p>${coverage.supreme_court_count} Supreme Court, ${coverage.high_court_count} High Courts, and ${coverage.state_ut_aggregate_count} state/UT aggregates for district and subordinate courts, as reported in the cited answer.</p></article><article class="panel"><p class="eyebrow">LIMITATIONS</p><h2>What is not established</h2><p>The source does not state tribunal coverage or individual district-court coverage. State/UT aggregates must not be read as district observations.</p></article><article class="panel"><p class="eyebrow">AUTOMATION</p><h2>Daily verification, no live API</h2><p>Daily source verification is scheduled to check for newer official reports and validate any replacement. No automatic public data API is connected. A failed or uncertain check keeps the last verified snapshot visible with a warning.</p></article><article class="panel"><p class="eyebrow">SOURCE TERMS</p><h2>Review before commercial use</h2><p>Reuse and commercial publication terms for the government report have not been verified. Confirm the applicable reuse terms and attribution requirements before commercial use; this project does not claim commercial data clearance.</p></article></section><p class="method-note">A separate 2023 registered-crime map is available under Research tools. It is not joined to court pendency. No individual case or personal data is included.</p>`;
}

function drawOfficialBars(rows) {
  const canvas=document.getElementById('official-state-bars');if(!canvas)return;
  if(!window.Chart){canvas.insertAdjacentHTML('afterend','<p class="chart-method">Chart library unavailable.</p>');return;}
  charts.get('official-state-bars')?.destroy();const wrap=canvas.closest('.chart-wrap');if(wrap)wrap.style.height=`${Math.max(500,rows.length*22)}px`;
  const css=getComputedStyle(document.documentElement),pending=css.getPropertyValue('--chart-pending').trim(),text=css.getPropertyValue('--chart-text').trim(),grid=css.getPropertyValue('--chart-grid').trim();
  charts.set('official-state-bars',new Chart(canvas,{type:'bar',data:{labels:rows.map(r=>r.state),datasets:[{label:'Reported pending cases',data:rows.map(r=>r.cases_pending),backgroundColor:pending,borderColor:pending}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${n(c.raw)} pending cases`}}},scales:{x:{beginAtZero:true,grid:{color:grid},ticks:{color:text,callback:n}},y:{grid:{display:false},ticks:{color:text,font:{size:10}}}}}}));
}

function renderOfficialOverview(snapshot) {
  const combined=snapshot.reported_categories_combined,metrics=snapshot.summary_metrics.reported_categories_combined;
  document.getElementById('official-pending').textContent=n(combined.cases_pending);document.getElementById('official-pending').title=new Intl.NumberFormat('en-IN').format(combined.cases_pending);
  document.getElementById('official-share').textContent=pct(metrics.share_pending_over_5y.value);
  document.getElementById('official-level-totals').innerHTML=Object.entries(snapshot.totals_by_level).map(([key,v])=>`<tr><td>${levelNames[key]}</td><td class="numeric">${n(v.reporting_units)}</td><td class="numeric">${n(v.cases_pending)}</td><td class="numeric">${n(v.cases_pending_over_5y)}</td></tr>`).join('');
  drawOfficialBars(snapshot.records.filter(r=>r.court_level==='district_subordinate_aggregate').sort((a,b)=>b.cases_pending-a.cases_pending));
}

function renderOfficialState(snapshot, previousState) {
  const rows=snapshot.records.filter(r=>r.court_level==='district_subordinate_aggregate').sort((a,b)=>a.state.localeCompare(b.state)),select=document.getElementById('official-state-select');
  select.innerHTML=rows.map(r=>`<option value="${esc(r.court_id)}">${esc(r.state)}</option>`).join('');
  if (previousState && rows.some(r=>r.court_id===previousState)) select.value=previousState;
  const draw=()=>{const row=rows.find(r=>r.court_id===select.value);if(!row)return;document.getElementById('official-state-pending').textContent=n(row.cases_pending);document.getElementById('official-state-over5').textContent=n(row.cases_pending_over_5y);document.getElementById('official-state-share').textContent=pct(row.metrics.share_pending_over_5y.value);document.getElementById('official-state-coverage').textContent='1 published state/UT aggregate';document.getElementById('official-state-row').innerHTML=`<tr><td>District and subordinate courts aggregate</td><td>${esc(row.state)}</td><td>${esc(row.snapshot_date)}</td><td class="numeric">${n(row.cases_pending)}</td><td class="numeric">${n(row.cases_pending_over_5y)}</td><td class="numeric">${pct(row.metrics.share_pending_over_5y.value)}</td></tr>`;};
  select.addEventListener('change',draw);draw();
}

function renderOfficialCoverage(snapshot, previousState, previousLevel, previousSort) {
  const rows=snapshot.records,state=document.getElementById('official-state-filter'),level=document.getElementById('official-level-filter'),sort=document.getElementById('official-sort');
  state.insertAdjacentHTML('beforeend',[...new Set(rows.filter(r=>r.state).map(r=>r.state))].sort().map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join(''));
  if (previousState && [...state.options].some(o=>o.value===previousState)) state.value=previousState;
  if (previousLevel) level.value=previousLevel;
  if (previousSort) sort.value=previousSort;
  let view=[];const granularity={supreme_court:'Supreme Court',high_court:'High Court',district_subordinate_aggregate:'State/UT aggregate (district/subordinate)'};
  const draw=()=>{view=rows.filter(r=>(!state.value||r.state===state.value)&&(!level.value||r.court_level===level.value));const key=sort.value;view.sort((a,b)=>key==='court_label'?a.court_label.localeCompare(b.court_label):b[key]-a[key]);document.getElementById('official-row-count').textContent=`${view.length} of ${rows.length} reporting units`;document.getElementById('official-rows').innerHTML=view.length?view.map(r=>`<tr><td>${esc(r.court_label)}</td><td>${granularity[r.court_level]}</td><td>${esc(r.state||'Not applicable')}</td><td>${esc(r.snapshot_date)}</td><td class="numeric">${n(r.cases_pending)}</td><td class="numeric">${n(r.cases_pending_over_5y)}</td><td class="numeric">${pct(r.metrics.share_pending_over_5y.value)}</td></tr>`).join(''):'<tr><td colspan="7">No reporting units match these filters.</td></tr>';};
  state.addEventListener('change',draw);level.addEventListener('change',draw);sort.addEventListener('change',draw);
  document.getElementById('official-download').addEventListener('click',()=>{const cols=['court_label','court_level','state','snapshot_date','cases_pending','cases_pending_over_5y','share_pending_over_5y','source_table','source_url'];const quote=v=>{let x=String(v??'');if(/^[=+\-@]/.test(x))x=`'${x}`;return `"${x.replaceAll('"','""')}"`;};const content=[cols.map(quote).join(','),...view.map(r=>cols.map(c=>quote(c==='share_pending_over_5y'?r.metrics[c].value:c==='source_url'?snapshot.source.source_url:r[c])).join(','))].join('\r\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([content],{type:'text/csv'}));a.download=`official-court-coverage-${snapshot.data_as_of}-filtered.csv`;a.click();URL.revokeObjectURL(a.href);});draw();
}

export function renderOfficialRoute(route,snapshot,refresh,statusFn,extras={}) {
  const stateValue=document.getElementById('official-state-select')?.value;
  const levelValue=document.getElementById('official-level-filter')?.value;
  const stateFilter=document.getElementById('official-state-filter')?.value;
  const sortValue=document.getElementById('official-sort')?.value;
  const root=document.getElementById('official-view');
  if(researchRoutes.includes(route)){
    const saved=Object.fromEntries([...root.querySelectorAll('select')].map(x=>[x.id,x.value]));
    renderResearch(route,snapshot,refresh,extras,root);
    for(const [id,value] of Object.entries(saved)){const input=document.getElementById(id);if(input&&[...input.options].some(x=>x.value===value)){input.value=value;input.dispatchEvent(new Event('change',{bubbles:true}));}}
    if(!reportRoutes.includes(route))addResearchActions(root,snapshot,refresh,extras,route);return;
  }
  root.innerHTML=markup(route,snapshot,refresh);statusFn(`${snapshot.records.length} official reporting units loaded. Historical snapshot as of ${dateLabel(snapshot.data_as_of)}.`,'success');
  if(route==='overview')renderOfficialOverview(snapshot);if(route==='state')renderOfficialState(snapshot,stateValue);if(route==='district')renderOfficialCoverage(snapshot,stateFilter,levelValue,sortValue);
  root.insertAdjacentHTML('afterbegin',courtLinks());
  addResearchActions(root,snapshot,refresh,extras,route);
}
