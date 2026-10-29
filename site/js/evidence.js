/** Top-three concentration uses only district/subordinate State/UT stocks, never higher courts. */
export function concentration(records) {
  const rows=records.filter(r=>r.court_level==='district_subordinate_aggregate');
  if(!rows.length||rows.some(r=>!Number.isFinite(r.cases_pending)||r.cases_pending<0))return null;
  const total=rows.reduce((n,r)=>n+r.cases_pending,0);
  if(!total)return null;
  const top=[...rows].sort((a,b)=>b.cases_pending-a.cases_pending).slice(0,3);
  return {top,total,share:top.reduce((n,r)=>n+r.cases_pending,0)/total};
}
/** Distinct loaded districts and dates; no national denominator or completeness claim. */
export function districtCoverage(records=[]) {
  const rows=records.filter(r=>r.court_level==='district');
  return {districts:[...new Set(rows.map(r=>`${r.district}, ${r.state}`))].sort(),months:[...new Set(rows.map(r=>r.month))].sort()};
}
