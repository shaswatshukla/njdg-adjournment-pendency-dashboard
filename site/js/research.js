// Research tools share the verified snapshot; crime remains an independent series.
import { reportRoutes, renderCourtReports } from './court-reports.js?v=0.4.0';
const e = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = v => v == null ? 'Unavailable' : new Intl.NumberFormat('en-IN').format(v);
const share = r => r.cases_pending ? r.cases_pending_over_5y / r.cases_pending : null;
const pct = v => v == null ? 'Unavailable' : `${(100 * v).toFixed(1)}%`;
export const researchRoutes = ['health', 'archive', 'compare', 'breakdowns', 'crime',...reportRoutes];
const labels = ['Data health', 'Snapshot archive', 'Compare states', 'Breakdowns', 'Crime map','High Courts','Supreme Court','District reports','Periodic publications'];
const states = s => s.records.filter(r => r.court_level === 'district_subordinate_aggregate');
const options = (rows, key = 'state') => rows.map(r => `<option value="${e(r[key])}">${e(r[key])}</option>`).join('');
const source = (s, table) => `<a class="source-inline" href="${e(s.source.source_url)}#page=${s.source.source_pages[table]}" target="_blank" rel="noopener">${e(table)} · p. ${s.source.source_pages[table]}</a>`;
const age = date => Math.max(0, Math.floor((Date.now() - Date.parse(date)) / 86400000));
function table(rows, s) {
  return `<div class="table-scroll"><table><thead><tr><th>Reporting unit</th><th>Pending</th><th>Over 5 years</th><th>Share over 5 years</th><th>Source</th></tr></thead><tbody>${rows.length ? rows.map(r => `<tr><td>${e(r.court_label)}</td><td>${num(r.cases_pending)}</td><td>${num(r.cases_pending_over_5y)}</td><td>${pct(share(r))}</td><td>${source(s, r.source_table)}</td></tr>`).join('') : '<tr><td colspan="5">No data for this selection.</td></tr>'}</tbody></table></div>`;
}
function chrome(route, s) {
  return `<p class="breadcrumb"><a href="#overview">Overview</a> / Research tools / ${labels[researchRoutes.indexOf(route)]}</p><section class="page-heading"><p class="eyebrow">RESEARCH TOOLS</p><h1>${labels[researchRoutes.indexOf(route)]}</h1><p>Court coverage: ${e(s.data_as_of)} · ${s.records.length} published reporting units. Crime data has its own reporting year.</p></section><nav class="research-nav" aria-label="Research tools">${researchRoutes.map((r, i) => `<a href="#${r}" ${r === route ? 'aria-current="page"' : ''}>${labels[i]}</a>`).join('')}</nav><div id="research-content"></div>`;
}
function health(s, refresh, root, meta) {
  const missing = ['Institutions', 'Disposals', 'Hearings', 'Adjournments', 'Over-three-year counts', 'District rows', 'Civil/criminal split'];
  root.innerHTML = `<section class="kpi-grid"><article class="kpi"><p>Age of court data</p><strong>${age(s.data_as_of)} days</strong><small>Measured from the reporting date, not build time</small></article><article class="kpi"><p>Last successful source verification</p><strong>${e(refresh?.last_successful_checked_at_utc || (['verified_snapshot','updated','no_change'].includes(refresh?.status) ? refresh.last_checked_at_utc : 'Not recorded'))}</strong><small>Latest attempt: ${e(refresh?.last_checked_at_utc || 'Unknown')}</small></article><article class="kpi"><p>Latest check result</p><strong>${e(refresh?.status || 'Unknown')}</strong><small>Daily checks do not make old data current</small></article><article class="kpi"><p>Published coverage</p><strong>${s.coverage.state_ut_aggregate_count}/36 States/UTs</strong><small>${s.coverage.high_court_count} High Courts and ${s.coverage.supreme_court_count} Supreme Court</small></article></section><section class="panel"><h2>Verification and build status</h2><p>${e(refresh?.note || 'No check details available.')}</p><p>Last pipeline build: ${e(meta?.generated_at_utc || 'Unavailable')} · Rejected rows in that successful build: ${num(meta?.rejected_rows)}</p><p>Failed checks: ${['error','needs_review'].includes(refresh?.status) ? 'Latest attempt needs attention; last verified counts are retained.' : 'No failure reported by the latest recorded attempt.'} A complete check history is not yet recorded; this is not a lifetime failure count.</p><p>Data reuse terms: <strong>unverified</strong>. Individual district/court and tribunal coverage: <strong>not established</strong>.</p></section><section class="panel"><h2>Field availability</h2><p>Available: pending stock, over-five-year stock and derived over-five-year share.</p><ul>${missing.map(x => `<li>${x}: unavailable in this court source</li>`).join('')}</ul></section>`;
}
export function comparable(a, b) {
  return a.data_as_of !== b.data_as_of && a.source.source_url === b.source.source_url &&
    JSON.stringify(a.records.map(r => [r.court_id, r.court_level, r.source_table]).sort()) === JSON.stringify(b.records.map(r => [r.court_id, r.court_level, r.source_table]).sort());
}
function archive(s, data, root) {
  const items = data?.snapshots || [];
  if (!items.length) { root.innerHTML = '<section class="panel">No verified archive is available.</section>'; return; }
  root.innerHTML = `<section class="panel"><h2>Verified reporting dates</h2><p>${items.length} date(s) archived. No monthly values are inferred between releases.</p><div class="filter-panel"><label>Snapshot<select id="archive-date">${items.map(x => `<option>${e(x.data_as_of)}</option>`).join('')}</select></label><label>Compare with<select id="archive-other"><option value="">Choose another reporting date</option>${items.map(x => `<option>${e(x.data_as_of)}</option>`).join('')}</select></label></div><div id="archive-comparison" role="status"></div><div id="archive-table"></div></section>`;
  const draw = () => {
    const a = items.find(x => x.data_as_of === root.querySelector('#archive-date').value);
    const b = items.find(x => x.data_as_of === root.querySelector('#archive-other').value);
    root.querySelector('#archive-table').innerHTML = `<p>Reporting date: ${e(a.data_as_of)}. ${e(a.source.title)}.</p>${table(a.records, a)}`;
    const out = root.querySelector('#archive-comparison');
    if (!b) out.textContent = items.length < 2 ? 'A second verified date is needed to calculate change.' : 'Select another date to inspect comparability.';
    else if (!comparable(a,b)) out.textContent = 'Change calculation withheld: same date, changed source, or changed coverage/table definitions. Review the source definitions before comparison.';
    else out.innerHTML = `<p>Coverage and source identifiers match; this does not establish unchanged statistical definitions. Review both reports before interpreting changes.</p><div class="table-scroll"><table><thead><tr><th>Unit</th><th>Pending difference (${e(a.data_as_of)} minus ${e(b.data_as_of)})</th><th>Over-5-year share difference</th></tr></thead><tbody>${a.records.map(r => {const q = b.records.find(x => x.court_id === r.court_id); return `<tr><td>${e(r.court_label)}</td><td>${num(r.cases_pending - q.cases_pending)}</td><td>${share(r) == null || share(q) == null ? 'Unavailable' : ((share(r)-share(q))*100).toFixed(1)+' percentage points'}</td></tr>`;}).join('')}</tbody></table></div>`;
  };
  root.querySelectorAll('select').forEach(x => x.addEventListener('change', draw));
  root.querySelector('#archive-date').value = items.at(-1).data_as_of;
  draw();
}
function compare(s, root) {
  const rows = states(s).sort((a,b) => a.state.localeCompare(b.state));
  root.innerHTML = `<section class="panel"><div class="filter-panel"><label>State/UT A<select id="compare-a">${options(rows)}</select></label><label>State/UT B<select id="compare-b">${options(rows)}</select></label></div><p>Same reporting date and district/subordinate aggregate definition. Raw counts reflect jurisdiction size; neither counts nor age shares establish court quality.</p><div id="compare-results"></div></section>`;
  root.querySelector('#compare-b').selectedIndex = Math.min(1,rows.length-1);
  const draw = () => {
    const selected = ['a','b'].map(x => rows.find(r => r.state === root.querySelector('#compare-'+x).value));
    root.querySelector('#compare-results').innerHTML = table(selected, s) + `<p>Pending difference (A minus B): <strong>${num(selected[0].cases_pending-selected[1].cases_pending)}</strong>. Over-5-year share difference: <strong>${share(selected[0]) == null || share(selected[1]) == null ? 'Unavailable' : ((share(selected[0])-share(selected[1]))*100).toFixed(1)+' percentage points'}</strong>.</p>`;
  };
  root.querySelectorAll('select').forEach(x => x.addEventListener('change',draw)); draw();
}
function breakdowns(s, root) {
  root.innerHTML = `<section class="panel"><label>Reporting level<select id="breakdown-level"><option value="">All levels</option><option value="supreme_court">Supreme Court</option><option value="high_court">High Courts</option><option value="district_subordinate_aggregate">State/UT district/subordinate aggregates</option></select></label><div id="breakdown-results"></div></section><section class="panel"><h2>Additional breakdowns</h2><div class="table-scroll"><table><thead><tr><th>Breakdown</th><th>Available detail</th></tr></thead><tbody><tr><td>Age</td><td>Over five years and five years or less (derived remainder). Finer age bands unavailable.</td></tr><tr><td>Civil/criminal</td><td>Not reported in this court source</td></tr><tr><td>Institutions and disposals</td><td>Not reported in this court source</td></tr><tr><td>Hearing and adjournment counts</td><td>Not reported in this court source</td></tr></tbody></table></div><p>Crime registrations are an independent police series, not a criminal-court breakdown.</p></section>`;
  const draw = () => {const rows = s.records.filter(r => !root.querySelector('select').value || r.court_level === root.querySelector('select').value);const pending = rows.reduce((n,r)=>n+r.cases_pending,0), old = rows.reduce((n,r)=>n+r.cases_pending_over_5y,0);root.querySelector('#breakdown-results').innerHTML = `<p>Reported pending: <strong>${num(pending)}</strong> · Over five years: <strong>${num(old)}</strong> · Five years or less: <strong>${num(pending-old)}</strong> (derived: pending minus over five years).</p>${table(rows,s)}`;};
  root.querySelector('select').addEventListener('change',draw); draw();
}
// Approximate tile locations only: not boundaries, coordinates, or an official political map.
const positions = {'Ladakh':[4,0],'Jammu and Kashmir':[3,1],'Himachal Pradesh':[4,2],'Punjab':[3,2],'Chandigarh':[3,3],'Uttarakhand':[5,3],'Haryana':[3,4],'Delhi':[4,4],'Rajasthan':[2,5],'Uttar Pradesh':[5,4],'Bihar':[7,4],'Sikkim':[8,3],'Arunachal Pradesh':[11,2],'Assam':[10,3],'Nagaland':[12,3],'Manipur':[12,4],'Mizoram':[11,5],'Tripura':[10,5],'Meghalaya':[10,4],'West Bengal':[8,5],'Jharkhand':[7,5],'Gujarat':[1,6],'Madhya Pradesh':[4,6],'Chhattisgarh':[6,6],'Odisha':[7,7],'Maharashtra':[3,7],'Dadra and Nagar Haveli and Daman and Diu':[1,7],'Goa':[2,8],'Karnataka':[3,9],'Telangana':[5,8],'Andhra Pradesh':[5,9],'Tamil Nadu':[4,11],'Puducherry':[5,11],'Kerala':[3,11],'Lakshadweep':[1,11],'Andaman and Nicobar Islands':[10,11]};
function crime(data, root, check) {
  if (!data?.records?.length) {root.innerHTML='<section class="panel">No verified aggregate crime data is available.</section>';return;}
  root.innerHTML = `<div class="alert"><strong>${data.year} registered crimes · Historical annual data.</strong> This is a schematic tile map, not geographic boundaries or a safety ranking. Court figures remain dated separately.</div><section class="panel"><div class="filter-panel"><label>Measure<select id="crime-measure"><option value="total">IPC + SLL registered cases</option><option value="ipc">IPC registered cases</option><option value="sll">SLL registered cases</option></select></label><label>State/UT<select id="crime-state">${options(data.records)}</select></label></div><p>Each equally sized tile represents one State/UT. Darker shading means more registered cases; counts are not adjusted for population.</p><div class="crime-map-scroll"><div id="crime-map" class="crime-map" role="group" aria-label="Schematic State and UT registered crime tile map"></div></div><p id="crime-detail" role="status" aria-live="polite"></p><p class="map-legend">Light to dark: lower to higher counts, five equal-width bands from zero to the selected national maximum.</p><div id="crime-table"></div><p>Source: <a href="${e(data.source.source_url)}#page=3" target="_blank" rel="noopener">MHA, Rajya Sabha Question 407, 3 December 2025, Annexure I, PDF page 3</a>; underlying NCRB Crime in India. <strong>Reuse terms unverified.</strong></p></section><section class="panel"><h2>How to read this map</h2><ul>${data.limitations.map(x=>`<li>${e(x)}</li>`).join('')}</ul><p>No per-lakh rate is calculated because no matching population denominator is loaded.</p><p><strong>IPC → BNS, 1 July 2024:</strong> this map uses pre-transition 2023 IPC and SLL categories only. The mapping table marks totals as not directly comparable; no BNS year is spliced into this series.</p></section>`;
  const draw = () => {
    const key=root.querySelector('#crime-measure').value, selected=root.querySelector('#crime-state').value;
    const max=Math.max(...data.records.map(r=>r[key]));
    root.querySelector('#crime-map').innerHTML=data.records.map((r,i)=>{const pos=positions[r.state]||[i%13,13+Math.floor(i/13)], band=Math.min(4,Math.floor(r[key]/(max||1)*5));return `<button type="button" class="crime-tile band-${band}" style="grid-column:${pos[0]+1};grid-row:${pos[1]+1}" data-state="${e(r.state)}" aria-pressed="${r.state===selected}" aria-label="${e(r.state)}, ${num(r[key])} registered cases in ${data.year}" title="${e(r.state)}: ${num(r[key])}">${e(r.state)}</button>`;}).join('');
    const row=data.records.find(r=>r.state===selected);
    root.querySelector('#crime-detail').textContent=`${row.state}: ${num(row[key])} registered cases (${data.year}). ${data.method}`;
    root.querySelector('#crime-table').innerHTML=`<div class="table-scroll"><table><caption>Accessible table · ${data.year} · exact counts</caption><thead><tr><th>State/UT</th><th>IPC</th><th>SLL</th><th>IPC + SLL</th></tr></thead><tbody>${[...data.records].sort((a,b)=>b[key]-a[key]).map(r=>`<tr><td>${e(r.state)}</td><td>${num(r.ipc)}</td><td>${num(r.sll)}</td><td>${num(r.total)}</td></tr>`).join('')}</tbody></table></div>`;
  };
  root.querySelectorAll('select').forEach(x=>x.addEventListener('change',draw));
  const verification=document.createElement('p');verification.className='method-note';verification.textContent=`Crime source verification: ${check?.status || 'not recorded'}; last attempt ${check?.last_checked_at_utc || 'unknown'}. Crime reporting year remains ${data.year}. Daily review is scheduled; a changed classification requires review before ingestion.`;root.prepend(verification);
  root.querySelector('#crime-map').addEventListener('click',ev=>{const button=ev.target.closest('button[data-state]');if(!button)return;root.querySelector('#crime-state').value=button.dataset.state;draw();root.querySelectorAll('button[data-state]').forEach(x=>{if(x.dataset.state===button.dataset.state)x.focus();});}); draw();
}
export function renderResearch(route,s,refresh,extras,root) {
  root.innerHTML=chrome(route,s);const content=root.querySelector('#research-content');
  if(reportRoutes.includes(route)){renderCourtReports(route,s,extras.periodic,content);return;}
  if(route==='health')health(s,refresh,content,extras.meta);
  if(route==='archive')archive(s,extras.archive,content);
  if(route==='compare')compare(s,content);
  if(route==='breakdowns')breakdowns(s,content);
  if(route==='crime')crime(extras.crime,content,refresh?.crime_check);
}
export function addResearchActions(root,s,refresh,extras,route) {
  // Source links beside existing cards and numeric cells, with computation notes.
  if (!researchRoutes.includes(route)) {
    root.querySelectorAll('.kpi').forEach(card=>{const d=document.createElement('details');d.className='metric-source';d.innerHTML=`<summary>Source & calculation</summary><p>Reporting date ${e(s.data_as_of)}. ${e(card.querySelector('small')?.textContent || 'Reported count; ratios use reported counts.')}</p><p>${s.source.source_tables.map(t=>source(s,t)).join(' · ')}</p>`;card.append(d);});
    const annotate = () => root.querySelectorAll('td.numeric').forEach(cell=>{if(cell.querySelector('.source-inline'))return;const row=cell.parentElement.textContent;const record=s.records.find(r=>row.includes(r.court_label)|| (r.state&&row.includes(r.state)));const t=record?.source_table || s.source.source_table_by_level[row.includes('High Court')?'high_court':row.includes('Supreme Court')?'supreme_court':'district_subordinate_aggregate'];cell.insertAdjacentHTML('beforeend',`<small>${source(s,t)}</small>`);});
    annotate();root.onchange=annotate;
  }
  const tools=document.createElement('div');tools.className='research-actions';tools.innerHTML='<a href="#health">Check data health</a><a href="#compare">Compare States/UTs</a><button type="button" class="button-secondary" id="print-brief">Print / save research brief as PDF</button>';root.prepend(tools);
  root.querySelector('#print-brief').addEventListener('click',()=>{
    let report=document.getElementById('print-report');if(!report){report=document.createElement('section');report.id='print-report';document.body.append(report);}
    let rows=s.records;
    const selected=root.querySelector('#official-state-select')?.value;
    if(selected)rows=rows.filter(r=>r.court_id===selected);
    const sf=root.querySelector('#official-state-filter')?.value, lf=root.querySelector('#official-level-filter')?.value || root.querySelector('#breakdown-level')?.value;
    if(sf)rows=rows.filter(r=>r.state===sf);if(lf)rows=rows.filter(r=>r.court_level===lf);
    if(route==='compare'){const chosen=[root.querySelector('#compare-a').value,root.querySelector('#compare-b').value];rows=states(s).filter(r=>chosen.includes(r.state));}
    const archived=route==='archive'?extras.archive?.snapshots.find(x=>x.data_as_of===root.querySelector('#archive-date')?.value):null;
    const reportSnapshot=archived||s;if(archived)rows=archived.records;
    const isCrime=route==='crime';
    const crimeRow=isCrime?extras.crime.records.find(r=>r.state===root.querySelector('#crime-state')?.value):null;
    const crimeBrief=crimeRow?`<p>Selected measure: ${e(root.querySelector('#crime-measure').selectedOptions[0].textContent)}.</p><table><thead><tr><th>State/UT</th><th>IPC</th><th>SLL</th><th>IPC + SLL</th></tr></thead><tbody><tr><td>${e(crimeRow.state)}</td><td>${num(crimeRow.ipc)}</td><td>${num(crimeRow.sll)}</td><td>${num(crimeRow.total)}</td></tr></tbody></table>`:'';
    report.innerHTML=`<h1>Justice Metrics · Research brief</h1><p>View: ${e(root.querySelector('h1')?.textContent)} · Prepared ${new Date().toISOString().slice(0,10)}</p><p>${isCrime?'Crime reporting year: '+e(extras.crime?.year):'Court data as of '+e(reportSnapshot.data_as_of)} · Court source last checked ${e(refresh?.last_checked_at_utc || 'Unknown')}</p>${isCrime?crimeBrief:table(rows,reportSnapshot)}<h2>Source and method</h2><p>${isCrime?e(extras.crime?.method):'Pending and over-five-year counts are reported stocks. Share = over-five-year count ÷ pending; zero pending gives unavailable. Stocks are never summed across reporting dates. Institutions, disposals and adjournments are unavailable in this court source.'}</p><p>${isCrime?e(extras.crime?.source.source_url):e(reportSnapshot.source.title)+' · '+e(reportSnapshot.source.source_url)}</p><h2>Limitations</h2><ul>${(isCrime?extras.crime.limitations:reportSnapshot.limitations).map(x=>`<li>${e(x)}</li>`).join('')}</ul><p>Independent analysis only. Not legal advice; no outcome prediction or court-quality judgement. Figures may differ from current NJDG. Data commercial reuse terms remain unverified.</p>`;
    window.print();
  });
}
