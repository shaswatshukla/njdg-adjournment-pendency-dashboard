import { concentration, districtCoverage } from './evidence.js?v=0.8.0';
import { researchRoutes, renderResearch, addResearchActions } from './research.js?v=0.8.0';
import { reportRoutes, courtLinks } from './court-reports.js?v=0.8.0';
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
let officialRange = '10';
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
  if (route === 'overview') return `<section class="page-heading"><p class="eyebrow">INDIA / PUBLISHED COURT REPORTS</p><h1>Court pendency in India</h1><p>Three questions. One dated national snapshot. Clear limits on what can be compared.</p>${meta}</section>${status}<section class="answer-grid" aria-label="Three questions about pendency"><article class="panel answer-card"><h2>How many cases are pending?</h2><strong id="official-pending">Unavailable</strong><p id="pending-exact"></p><small>Supreme Court, High Courts and district/subordinate aggregates combined; not every judicial body.</small></article><article class="panel answer-card"><h2>Where is it concentrated?</h2><strong id="concentration-share">Unavailable</strong><p id="concentration-states"></p><small>Share of district/subordinate pending cases held by the three largest State/UT aggregates. Higher courts excluded.</small><a href="#state">Explore State/UT totals &rarr;</a></article><article class="panel answer-card"><h2>Is the backlog improving?</h2><strong class="answer-text">National trend unavailable</strong><p>A single nationwide reporting date cannot establish a direction.</p><a href="#supreme-court">View the separate Supreme Court historical series &rarr;</a><small>Jan–Aug 2025 only; this is not an all-India trend or a court performance score.</small></article></section><div class="alert"><strong>Historical data, partial district detail.</strong> National reporting date ${dateLabel(snapshot.data_as_of)}. State/UT totals are not district rows. <a href="#district-reports">See exactly which districts have reports</a>.</div><section class="chart-grid"><article class="panel chart-panel"><div class="panel-heading"><div><p class="eyebrow">BACKLOG CONCENTRATION</p><h2>Pending by State/UT aggregate</h2></div><span class="unit">Cases</span></div><div class="chart-wrap official-bars"><canvas id="official-state-bars" role="img" aria-label="Reported pending cases by state or union territory aggregate"></canvas></div><p class="chart-method">Published district/subordinate aggregates only. <a href="#district">Exact figures and CSV</a> remain available if the chart library cannot load.</p></article><article class="panel"><p class="eyebrow">PUBLISHED LEVEL TOTALS</p><h2>Which courts are included?</h2><div class="table-scroll"><table><thead><tr><th>Reporting category</th><th>Units</th><th>Pending</th><th>Over 5 years</th></tr></thead><tbody id="official-level-totals"></tbody></table></div><p class="chart-method">Distinct court categories; shared-jurisdiction High Courts are counted once.</p></article></section><section class="panel"><h2>Evidence before interpretation</h2><p>Over-five-year share across reported categories: <strong id="official-share"></strong>. This is an age share, not a clearance or adjournment rate. The national source does not report institutions, disposals or hearings.</p><p><a href="#health">Sources, dates and loading status</a> · <a href="#methodology">Definitions and limitations</a></p><p>Registered-crime statistics live in a separate context section. Crime registrations are annual flows; pending court cases are stocks. No causal comparison or combined score is calculated.</p></section>`;
  if (route === 'state') return `<p class="breadcrumb"><a href="#overview">Overview</a> / State explorer</p><section class="page-heading"><p class="eyebrow">OFFICIAL SNAPSHOT · STATE/UT</p><h1>State and UT aggregates</h1><p>Explore the published district and subordinate court aggregate for each state/UT.</p>${meta}</section><div class="alert"><strong>Granularity limit.</strong> This source does not provide district rows or monthly trends for these totals.</div>${status}<section class="panel controls"><label for="official-state-select">State or union territory<select id="official-state-select"></select></label><span id="official-state-coverage" class="unit"></span></section><section class="kpi-grid"><article class="kpi"><p>Reported pending</p><strong id="official-state-pending">-</strong><small>District/subordinate aggregate</small></article><article class="kpi"><p>Pending over 5 years</p><strong id="official-state-over5">-</strong><small>Reported nested age count</small></article><article class="kpi"><p>Over-5-year share</p><strong id="official-state-share">-</strong><small>Derived from reported counts</small></article><article class="kpi"><p>Monthly trends</p><strong>Unavailable</strong><small>One dated snapshot only</small></article></section><section class="panel table-panel"><div class="table-heading"><div><p class="eyebrow">SELECTED REPORTING UNIT</p><h2>District and subordinate courts</h2></div></div><div class="table-scroll"><table><thead><tr><th>Reporting unit</th><th>State/UT</th><th>Snapshot</th><th class="numeric">Pending</th><th class="numeric">Over 5 years</th><th class="numeric">Share over 5 years</th></tr></thead><tbody id="official-state-row"></tbody></table></div></section><p class="method-note">A state/UT aggregate does not support district rankings. The source does not report case-flow ratios.</p>`;
  if (route === 'district') return `<p class="breadcrumb"><a href="#overview">Overview</a> / Court coverage</p><section class="page-heading"><p class="eyebrow">OFFICIAL SNAPSHOT · REPORTING UNITS</p><h1>Court coverage</h1><p>Browse the ${coverage.published_reporting_units} reporting units in the parliamentary tables and export the filtered view.</p>${meta}</section><div class="alert"><strong>Level labels show source granularity.</strong> “State/UT aggregate” represents district and subordinate courts collectively; it is not one court.</div>${status}<section class="panel filter-panel"><label>Reporting level<select id="official-level-filter"><option value="">All levels</option><option value="supreme_court">Supreme Court</option><option value="high_court">High Courts</option><option value="district_subordinate_aggregate">State/UT aggregate</option></select></label><label>State/UT<select id="official-state-filter"><option value="">All states/UTs</option></select></label><label>Sort by<select id="official-sort"><option value="cases_pending">Pending, high to low</option><option value="cases_pending_over_5y">Over 5 years, high to low</option><option value="court_label">Reporting unit A-Z</option></select></label><button class="button-secondary" id="official-download" type="button">Download filtered CSV</button></section><section class="panel table-panel"><div class="table-heading"><div><p class="eyebrow">SOURCE SNAPSHOT</p><h2>Published reporting units</h2></div><span id="official-row-count" class="unit"></span></div><div class="table-scroll"><table><thead><tr><th>Reporting unit</th><th>Reporting level</th><th>State/UT</th><th>Snapshot date</th><th class="numeric">Pending</th><th class="numeric">Over 5 years</th><th class="numeric">Share over 5 years</th></tr></thead><tbody id="official-rows"></tbody></table></div></section>`;
  if (route === 'methodology') return `<p class="breadcrumb"><a href="#overview">Overview</a> / Methodology</p><section class="page-heading"><p class="eyebrow">OFFICIAL SNAPSHOT · METHODS</p><h1>What the source reports</h1><p>Counts are presented at their published reporting level; unreported measures remain unavailable.</p>${meta}</section><div class="alert alert-strong"><strong>Historical, cross-sectional data.</strong> This is not a live feed and cannot support monthly trends or case-flow rates.</div>${status}<section class="formula-grid"><article class="panel formula"><p class="eyebrow">REPORTED STOCK</p><h2>Pending cases</h2><code>Source reported count</code><p>The source snapshot reports the pending stock as of ${dateLabel(snapshot.data_as_of)}.</p></article><article class="panel formula"><p class="eyebrow">REPORTED AGE COUNT</p><h2>Pending over 5 years</h2><code>Source reported count</code><p>A nested age-band count, as published by reporting category.</p></article><article class="panel formula"><p class="eyebrow">DERIVED RATIO</p><h2>Over-5-year share</h2><code>Reported pending over 5 years ÷ reported pending</code><p>For combined totals, both counts are summed first; the ratio is not an average of category shares.</p></article><article class="panel formula"><p class="eyebrow">UNAVAILABLE</p><h2>Case-flow rates</h2><code>No numerator or denominator supplied</code><p>Institution, disposal, hearing, opening-stock, over-three-year, and monthly fields are not reported.</p></article></section><section class="panel"><p class="eyebrow">PRIMARY SOURCE</p><h2>${sourceTitle}</h2><p>Answered ${dateLabel(snapshot.source.answer_date)}; data as of ${dateLabel(snapshot.data_as_of)}.</p><ul><li><a href="${source}#page=${sourcePages[sourceTables.supreme_court]}" target="_blank" rel="noopener">${esc(sourceTables.supreme_court)}, PDF page ${sourcePages[sourceTables.supreme_court]}: Supreme Court and High Courts</a></li><li><a href="${source}#page=${sourcePages[sourceTables.district_subordinate_aggregate]}" target="_blank" rel="noopener">${esc(sourceTables.district_subordinate_aggregate)}, PDF page ${sourcePages[sourceTables.district_subordinate_aggregate]}: state/UT district and subordinate court aggregates</a></li></ul><p>Reuse/commercial terms have not been verified. The repository MIT license covers project code, not this source data.</p><p class="method-note"><strong>Refresh note:</strong> ${esc(refresh?.note || 'No refresh note is available.')}</p></section>`;
  return `<section class="page-heading"><p class="eyebrow">ABOUT THIS DATASET</p><h1>A verified historical source, with limits.</h1><p>The source and its coverage are shown for review. The data is not current/live and is not cleared for commercial reuse.</p>${meta}</section><div class="alert alert-strong"><strong>Commercial access is not verified.</strong> Reuse terms for the source data have not been confirmed. Do not assume the software MIT license grants data rights.</div>${status}<section class="two-column"><article class="panel"><p class="eyebrow">COVERAGE</p><h2>What is included</h2><p>${coverage.supreme_court_count} Supreme Court, ${coverage.high_court_count} High Courts, and ${coverage.state_ut_aggregate_count} state/UT aggregates for district and subordinate courts, as reported in the cited answer.</p></article><article class="panel"><p class="eyebrow">LIMITATIONS</p><h2>What is not established</h2><p>The source does not state tribunal coverage or individual district-court coverage. State/UT aggregates must not be read as district observations.</p></article><article class="panel"><p class="eyebrow">AUTOMATION</p><h2>Daily verification, no live API</h2><p>Daily source verification is scheduled to check for newer official reports and validate any replacement. No automatic public data API is connected. A failed or uncertain check keeps the last verified snapshot visible with a warning.</p></article><article class="panel"><p class="eyebrow">SOURCE TERMS</p><h2>Review before commercial use</h2><p>Reuse and commercial publication terms for the government report have not been verified. Confirm the applicable reuse terms and attribution requirements before commercial use; this project does not claim commercial data clearance.</p></article></section><p class="method-note">A separate 2023 registered-crime map is available under Research tools. It is not joined to court pendency. No individual case or personal data is included.</p>`;
}

function drawOfficialBars(rows) {
  const canvas=document.getElementById('official-state-bars');if(!canvas)return;
  if(!window.Chart){canvas.insertAdjacentHTML('afterend','<p class="chart-method">Chart library unavailable.</p>');return;}
  charts.get('official-state-bars')?.destroy();const wrap=canvas.closest('.chart-wrap');if(wrap)wrap.style.height=`${Math.max(320,rows.length*30)}px`;
  const css=getComputedStyle(document.documentElement),pending=css.getPropertyValue('--chart-pending').trim(),text=css.getPropertyValue('--chart-text').trim(),grid=css.getPropertyValue('--chart-grid').trim();
  charts.set('official-state-bars',new Chart(canvas,{type:'bar',data:{labels:rows.map(r=>r.state),datasets:[{label:'Reported pending cases',data:rows.map(r=>r.cases_pending),backgroundColor:pending,borderColor:pending,borderRadius:3,maxBarThickness:14}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${n(c.raw)} pending cases`}}},scales:{x:{beginAtZero:true,grid:{color:grid},ticks:{color:text,callback:n,maxTicksLimit:5,font:{size:12}},border:{display:false}},y:{grid:{display:false},ticks:{color:text,font:{size:12}},border:{display:false}}}}}));
}

function renderOfficialOverview(snapshot) {
  const combined=snapshot.reported_categories_combined,metrics=snapshot.summary_metrics.reported_categories_combined;
  document.getElementById('official-pending').textContent=`${(combined.cases_pending/10000000).toFixed(2)} Cr`;document.getElementById('official-pending').title=new Intl.NumberFormat('en-IN').format(combined.cases_pending);
  document.getElementById('official-share').textContent=pct(metrics.share_pending_over_5y.value);
  document.getElementById('pending-exact').textContent=`${new Intl.NumberFormat('en-IN').format(combined.cases_pending)} reported pending cases`;
  document.querySelector('.answer-grid').insertAdjacentHTML('afterend',`<p class="method-note">National source: <a href="${esc(snapshot.source.source_url)}#page=53">Annex I, PDF p.53 (Supreme Court and High Courts)</a> and <a href="${esc(snapshot.source.source_url)}#page=54">Annex II, PDF p.54 (State/UT district aggregates)</a>. Concentration is derived by summing the three largest State/UT stocks and dividing by all loaded State/UT stocks; it is not a population-adjusted rate.</p>`);
  const focus=concentration(snapshot.records);
  document.getElementById('concentration-share').textContent=focus?pct(focus.share):'Unavailable';
  document.getElementById('concentration-states').textContent=focus?focus.top.map(r=>r.state).join(', '):'No comparable State/UT counts.';
  document.getElementById('official-level-totals').innerHTML=Object.entries(snapshot.totals_by_level).map(([key,v])=>`<tr><td>${levelNames[key]}</td><td class="numeric">${n(v.reporting_units)}</td><td class="numeric">${n(v.cases_pending)}</td><td class="numeric">${n(v.cases_pending_over_5y)}</td></tr>`).join('');
  const rows=snapshot.records.filter(r=>r.court_level==='district_subordinate_aggregate').sort((a,b)=>b.cases_pending-a.cases_pending);
  const chartPanel=document.getElementById('official-state-bars').closest('.panel');
  const exact=document.createElement('details');exact.className='exact-chart-data';exact.innerHTML=`<summary>Exact values for all ${rows.length} State/UT aggregates</summary><div class="table-scroll" tabindex="0" role="region" aria-label="Exact State and UT pending cases"><table><caption>District/subordinate stock on ${esc(snapshot.data_as_of)}; not individual district figures</caption><thead><tr><th scope="col">State/UT</th><th scope="col">Pending</th><th scope="col">Over five years</th></tr></thead><tbody>${rows.map(r=>`<tr><td><a href="states/${r.state.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')}/">${esc(r.state)}</a></td><td>${new Intl.NumberFormat('en-IN').format(r.cases_pending)}</td><td>${new Intl.NumberFormat('en-IN').format(r.cases_pending_over_5y)}</td></tr>`).join('')}</tbody></table></div>`;chartPanel.append(exact);

  const controls=document.createElement('div');controls.className='chart-range';controls.setAttribute('role','group');controls.setAttribute('aria-label','State comparison coverage');
  controls.innerHTML='<button type="button" data-range="10">Top 10</button><button type="button" data-range="all">All 36</button>';
  chartPanel.querySelector('.panel-heading .unit').replaceWith(controls);
  const count=document.createElement('span');count.className='chart-coverage';chartPanel.querySelector('.chart-method').prepend(count);
  const draw=()=>{controls.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.range===officialRange)));const view=officialRange==='all'?rows:rows.slice(0,10);count.textContent=`${view.length} of ${rows.length} State/UT aggregates shown. `;drawOfficialBars(view);};
  controls.addEventListener('click',event=>{const button=event.target.closest('button');if(button){officialRange=button.dataset.range;draw();}});draw();
  const categoryTable=document.getElementById('official-level-totals').closest('.table-scroll');
  const levelLinks={supreme_court:'supreme-court',high_court:'high-courts',district_subordinate_aggregate:'state'};
  categoryTable.closest('.panel').classList.add('level-panel');
  categoryTable.outerHTML='<div class="level-cards">'+['supreme_court','high_court','district_subordinate_aggregate'].map((key,i)=>{const v=snapshot.totals_by_level[key];return [key,v];}).map(([key,v],i)=>{const table=snapshot.source.source_table_by_level[key];const page=snapshot.source.source_pages[table];return `<article class="level-card"><div class="level-card-top"><span class="level-index">0${i+1}</span><a href="#${levelLinks[key]}">${levelNames[key]} <span aria-hidden="true">↗</span></a></div><div class="level-card-value"><strong title="${new Intl.NumberFormat('en-IN').format(v.cases_pending)}">${n(v.cases_pending)}</strong><span>reported pending</span></div><p>${n(v.reporting_units)} reporting unit${v.reporting_units===1?'':'s'} · ${n(v.cases_pending_over_5y)} over 5 years</p><a class="source-inline" href="${esc(snapshot.source.source_url)}#page=${page}" target="_blank" rel="noopener">Source: ${esc(table)} · PDF page ${page}</a></article>`;}).join('')+'</div>';

}

function renderOfficialState(snapshot, previousState, periodic) {
  const rows=snapshot.records.filter(r=>r.court_level==='district_subordinate_aggregate').sort((a,b)=>a.state.localeCompare(b.state)),select=document.getElementById('official-state-select');
  select.innerHTML=rows.map(r=>`<option value="${esc(r.court_id)}">${esc(r.state)}</option>`).join('');
  const requestedState=new URLSearchParams(location.hash.split('?')[1]||'').get('state');
  if(requestedState){const chosen=rows.find(r=>r.state===requestedState);if(chosen)select.value=chosen.court_id;}
  if (!requestedState && previousState && rows.some(r=>r.court_id===previousState)) select.value=previousState;
  const detail=document.createElement('section');detail.className='panel';document.getElementById('official-view').append(detail);
  const draw=()=>{const row=rows.find(r=>r.court_id===select.value);
  if(row){const loaded=districtCoverage((periodic?.records||[]).filter(r=>r.state===row.state));detail.innerHTML=`<h2>District detail for ${esc(row.state)}</h2><p>${!periodic?'District report dataset unavailable or still loading.':loaded.districts.length?`${loaded.districts.length} loaded district: ${esc(loaded.districts.join('; '))}. Months: ${esc(loaded.months.join(', '))}.`:'No verified individual district report loaded for this State/UT. Missing coverage does not mean zero pending cases.'}</p><a href="#district-reports?state=${encodeURIComponent(row.state)}">Open district reports for this State/UT &rarr;</a>`;}
  if(!row)return;document.getElementById('official-state-pending').textContent=n(row.cases_pending);document.getElementById('official-state-over5').textContent=n(row.cases_pending_over_5y);document.getElementById('official-state-share').textContent=pct(row.metrics.share_pending_over_5y.value);document.getElementById('official-state-coverage').textContent='1 published state/UT aggregate';document.getElementById('official-state-row').innerHTML=`<tr><td>District and subordinate courts aggregate</td><td>${esc(row.state)}</td><td>${esc(row.snapshot_date)}</td><td class="numeric">${n(row.cases_pending)}</td><td class="numeric">${n(row.cases_pending_over_5y)}</td><td class="numeric">${pct(row.metrics.share_pending_over_5y.value)}</td></tr>`;};
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
    for(const [id,value] of Object.entries(saved)){if(id==='report-state'&&new URLSearchParams(location.hash.split('?')[1]||'').has('state'))continue;const input=document.getElementById(id);if(input&&[...input.options].some(x=>x.value===value)){input.value=value;input.dispatchEvent(new Event('change',{bubbles:true}));}}
    if(!reportRoutes.includes(route))addResearchActions(root,snapshot,refresh,extras,route);return;
  }
  root.innerHTML=markup(route,snapshot,refresh);statusFn(`${snapshot.records.length} official reporting units loaded. Historical snapshot as of ${dateLabel(snapshot.data_as_of)}.`,'success');
  if(route==='overview')renderOfficialOverview(snapshot);if(route==='state')renderOfficialState(snapshot,stateValue,extras.periodic||{records:extras.districtCoverageRows||[]});if(route==='district')renderOfficialCoverage(snapshot,stateFilter,levelValue,sortValue);
  
  addResearchActions(root,snapshot,refresh,extras,route);
}

