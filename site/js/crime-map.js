const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=v=>v==null?'Unavailable':new Intl.NumberFormat('en-IN').format(v);
const measures={total:'IPC + SLL registered cases',ipc:'IPC registered cases',sll:'SLL registered cases'};
let boundaryRequest;
function loadBoundaries(){
  if(!boundaryRequest)boundaryRequest=fetch('./assets/maps/india-states.json').then(r=>{if(!r.ok)throw new Error('Boundary file could not be loaded');return r.json();}).catch(error=>{boundaryRequest=null;throw error;});
  return boundaryRequest;
}
export function stateLink(state,measure){return '#crime?'+new URLSearchParams({state,measure}).toString();}
export function bandFor(value,max){return Number.isFinite(value)&&Number.isFinite(max)&&value>=0&&max>=0?Math.min(4,Math.floor(value/(max||1)*5)):null;}

export async function renderCrimeMap(data,root,check){
  if(!data?.records?.length){root.innerHTML='<section class="panel">No verified aggregate crime data is available.</section>';return;}
  const rows=data.records,params=new URLSearchParams(location.hash.split('?')[1]||'');
  const initialState=rows.some(r=>r.state===params.get('state'))?params.get('state'):rows[0].state;
  const initialMeasure=Object.hasOwn(measures,params.get('measure'))?params.get('measure'):'total';
  root.innerHTML=`<div class="alert"><strong>${data.year} registered crimes · Historical annual data.</strong> Counts are not population-adjusted and do not measure personal safety. Court data has a separate reporting date.</div><section class="panel geographic-panel"><div class="panel-heading"><div><p class="eyebrow">INDIA · STATE & UT GEOGRAPHY</p><h2>Explore registered crime by place</h2></div><span class="unit">36 States/UTs</span></div><div id="crime-map-home"><div class="crime-map-frame" id="crime-map-frame"><div class="filter-panel"><label>Measure<select id="crime-measure">${Object.entries(measures).map(([v,label])=>`<option value="${v}">${label}</option>`).join('')}</select></label><label>State/UT<select id="crime-state">${[...rows].sort((a,b)=>a.state.localeCompare(b.state)).map(r=>`<option>${esc(r.state)}</option>`).join('')}</select></label></div><div class="map-toolbar"><div class="zoom-controls" role="group" aria-label="Map zoom"><button type="button" id="map-zoom-in" aria-label="Zoom in">+</button><button type="button" id="map-zoom-out" aria-label="Zoom out">−</button><button type="button" id="map-reset">Reset view</button><span id="map-zoom-level" class="unit" aria-live="polite">100%</span></div><button type="button" class="button-secondary" id="map-expand" aria-expanded="false" aria-controls="crime-map-dialog">Expand map ↗</button></div><div class="geo-layout"><div class="geo-map-stage" id="crime-map"><p id="map-load-status" role="status">Loading geographic boundaries...</p></div><aside class="crime-selection" aria-label="Selected State or Union Territory"><p class="eyebrow">SELECTED STATE / UT</p><h3 id="crime-selected-title"></h3><p id="crime-detail" role="status" aria-live="polite"></p><dl id="crime-selected-counts"></dl><a id="crime-permalink" class="text-link">Link to this State/UT ↗</a><a class="text-link" href="${esc(data.source.source_url)}#page=3" target="_blank" rel="noopener">Read the official source ↗</a><p class="method-note">Select a region or its label. Use +/− to zoom; drag a zoomed map to pan. Small UT dots are enlarged click targets, not area boundaries.</p></aside></div><div class="geo-legend" aria-label="Five colour bands from lower to higher registered counts"><span>Lower counts</span>${[0,1,2,3,4].map(i=>`<i class="band-${i}" aria-hidden="true"></i>`).join('')}<span>Higher counts</span></div><p class="map-legend" id="crime-band-ranges"></p><p class="map-attribution" id="map-attribution">Boundary vintage: 2024. Crime reporting year: ${data.year}. Geometry is for visual reference.</p></div></div><dialog class="crime-map-dialog" id="crime-map-dialog" aria-labelledby="expanded-map-title"><div class="expanded-map-header"><h2 id="expanded-map-title">India · Registered crime map</h2><button type="button" class="button-secondary" id="map-dialog-close">Close expanded map ×</button></div></dialog><details class="crime-table-disclosure"><summary>View all 36 States/UTs as an accessible table</summary><div id="crime-table"></div></details><p class="method-note">Crime source verification: ${esc(check?.status||'not recorded')}; last attempt ${esc(check?.last_checked_at_utc||'unknown')}. Daily source review is scheduled; reporting year remains ${data.year}.</p></section><section class="panel"><p class="eyebrow">SOURCE & INTERPRETATION</p><h2>What these figures can tell you</h2><p><a href="${esc(data.source.source_url)}#page=3" target="_blank" rel="noopener">MHA, Rajya Sabha Question 407, 3 December 2025, Annexure I, PDF page 3</a>; underlying NCRB Crime in India. Source reuse terms remain unverified.</p><ul>${data.limitations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><p>No per-lakh rate is calculated because no matching population denominator is loaded.</p><p><strong>IPC → BNS, 1 July 2024:</strong> this is pre-transition 2023 IPC/SLL data. No BNS year is spliced into this series.</p><p><a href="https://surveyofindia.gov.in/" target="_blank" rel="noopener">Survey of India</a> is the reference for authoritative boundaries. This simplified display is not a survey record.</p></section>`;
  const state=root.querySelector('#crime-state'),measure=root.querySelector('#crime-measure'),stage=root.querySelector('#crime-map');
  state.value=initialState;measure.value=initialMeasure;
  let svg,base,view,zoom=1,drag=null,dragged=false;
  function paint(){
    const key=measure.value,row=rows.find(r=>r.state===state.value),max=Math.max(...rows.map(r=>r[key]));
    root.querySelector('#crime-selected-title').textContent=row.state;
    root.querySelector('#crime-detail').textContent=`${num(row[key])} ${measures[key].toLowerCase()} · ${data.year}`;
    root.querySelector('#crime-selected-counts').innerHTML=[['IPC',row.ipc],['SLL',row.sll],['IPC + SLL',row.total]].map(([label,value])=>`<div><dt>${label}</dt><dd>${num(value)}</dd></div>`).join('');
    const link=stateLink(row.state,key);root.querySelector('#crime-permalink').href=link;history.replaceState(null,'',link);
    stage.querySelectorAll('.geo-state').forEach(a=>{
      const r=rows.find(x=>x.state===a.dataset.state),band=bandFor(r?.[key],max);
      a.setAttribute('class',`geo-state band-${band??'missing'}${r?.state===row.state?' selected':''}`);
      a.setAttribute('href',stateLink(r.state,key));a.setAttribute('aria-current',r.state===row.state?'true':'false');
      a.setAttribute('aria-label',`${r.state}: ${num(r[key])} ${measures[key].toLowerCase()} in ${data.year}. Open State/UT figures.`);
      a.querySelector('title').textContent=`${r.state}: ${num(r[key])} (${data.year})`;
    });
    root.querySelector('#crime-table').innerHTML=`<div class="table-scroll"><table><caption>${data.year} · exact registered-case counts · sorted by selected measure</caption><thead><tr><th>State/UT</th><th>IPC</th><th>SLL</th><th>IPC + SLL</th></tr></thead><tbody>${[...rows].sort((a,b)=>b[key]-a[key]).map(r=>`<tr><td><a href="${esc(stateLink(r.state,key))}" data-map-state="${esc(r.state)}">${esc(r.state)}</a></td><td class="numeric">${num(r.ipc)}</td><td class="numeric">${num(r.sll)}</td><td class="numeric">${num(r.total)}</td></tr>`).join('')}</tbody></table></div>`;
    const ranges=[0,1,2,3,4].map(i=>{const lo=i===0?0:Math.ceil(max*i/5),hi=i===4?max:Math.ceil(max*(i+1)/5)-1;return `${num(lo)}–${num(hi)}`;});
    root.querySelector('#crime-band-ranges').textContent=`Five equal-width count bands: ${ranges.join(' · ')}. Darker = more registered cases; counts are not crime rates or safety scores.`;
  }
  state.addEventListener('change',paint);measure.addEventListener('change',paint);
  root.addEventListener('click',event=>{
    const a=event.target.closest('a.geo-state,a[data-map-state]');if(!a||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
    event.preventDefault();if(dragged&&event.detail>0){dragged=false;return;}
    state.value=a.dataset.state||a.dataset.mapState;paint();
  });
  function updateView(){if(svg){svg.setAttribute('viewBox',view.join(' '));stage.classList.toggle('is-zoomed',zoom>1);root.querySelector('#map-zoom-level').textContent=`${Math.round(zoom*100)}%`;root.querySelector('#map-zoom-out').disabled=zoom<=1;root.querySelector('#map-zoom-in').disabled=zoom>=6;}}
  function clamp(){view[0]=Math.max(base[0],Math.min(base[2]-view[2],view[0]));view[1]=Math.max(base[1],Math.min(base[3]-view[3],view[1]));}
  function setZoom(next){if(!base)return;const cx=view[0]+view[2]/2,cy=view[1]+view[3]/2;zoom=Math.max(1,Math.min(6,next));view=[cx-base[2]/zoom/2,cy-base[3]/zoom/2,base[2]/zoom,base[3]/zoom];clamp();updateView();}
  root.querySelector('#map-zoom-in').addEventListener('click',()=>setZoom(zoom*1.4));
  root.querySelector('#map-zoom-out').addEventListener('click',()=>setZoom(zoom/1.4));
  root.querySelector('#map-reset').addEventListener('click',()=>{if(base){zoom=1;view=[...base];updateView();}});
  const dialog=root.querySelector('#crime-map-dialog'),frame=root.querySelector('#crime-map-frame'),home=root.querySelector('#crime-map-home'),expand=root.querySelector('#map-expand');
  expand.addEventListener('click',()=>{
    if(dialog.open){dialog.close();return;}
    dialog.append(frame);dialog.showModal();document.body.classList.add('crime-map-expanded');expand.setAttribute('aria-expanded','true');expand.textContent='Exit expanded view ↙';
  });
  root.querySelector('#map-dialog-close').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('close',()=>{home.append(frame);document.body.classList.remove('crime-map-expanded');expand.setAttribute('aria-expanded','false');expand.textContent='Expand map ↗';expand.focus();});
  paint();
  try{
    const boundaries=await loadBoundaries();if(!root.isConnected)return;
    const names=boundaries.features.map(f=>f.state);
    if(names.length!==36||new Set(names).size!==36||rows.some(r=>!names.includes(r.state)))throw new Error('Boundary-to-data coverage mismatch');
    if(boundaries.features.some(f=>!/^[-\d.,MLZ]+$/.test(f.path)||!f.label.every(Number.isFinite)))throw new Error('Invalid boundary path');
    base=boundaries.viewBox;view=[...base];
    stage.innerHTML=`<svg class="india-crime-svg" viewBox="${base.join(' ')}" role="group" aria-label="India geographic map: select any of the 36 States or Union Territories"><desc>Reference State/UT polygons coloured by 2023 registered-case counts. Select a region or use the dropdown and accessible table. Small Union Territory dots are enlarged targets.</desc>${boundaries.features.map(f=>`<a class="geo-state" data-state="${esc(f.state)}" tabindex="0" href="${esc(stateLink(f.state,measure.value))}"><title>${esc(f.state)}</title><path d="${f.path}" fill-rule="evenodd"/>${f.marker?`<circle class="ut-marker" cx="${f.label[0]}" cy="${f.label[1]}" r="6"/>`:''}<text class="geo-label" x="${f.label[0]}" y="${f.label[1]}" dy="${f.marker?-10:3}" text-anchor="middle" aria-hidden="true">${esc(f.abbr)}</text></a>`).join('')}</svg>`;
    svg=stage.querySelector('svg');svg.setAttribute('tabindex','0');
    svg.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home'].includes(event.key))return;if(event.key==='Home'){event.preventDefault();zoom=1;view=[...base];updateView();return;}if(zoom<=1)return;event.preventDefault();const delta=45/zoom;if(event.key==='ArrowLeft')view[0]-=delta;if(event.key==='ArrowRight')view[0]+=delta;if(event.key==='ArrowUp')view[1]-=delta;if(event.key==='ArrowDown')view[1]+=delta;clamp();updateView();});
    svg.addEventListener('pointerdown',event=>{if(zoom<=1||event.button!==0)return;const rect=svg.getBoundingClientRect();drag={id:event.pointerId,state:event.target.closest('a.geo-state')?.dataset.state,x:event.clientX,y:event.clientY,view:[...view],scale:Math.min(rect.width/view[2],rect.height/view[3])};dragged=false;svg.setPointerCapture(event.pointerId);});
    svg.addEventListener('pointermove',event=>{if(!drag||event.pointerId!==drag.id)return;const dx=event.clientX-drag.x,dy=event.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>4)dragged=true;view[0]=drag.view[0]-dx/drag.scale;view[1]=drag.view[1]-dy/drag.scale;clamp();updateView();});
    const end=event=>{if(drag?.id===event.pointerId){if(event.type==='pointerup'&&!dragged&&drag.state){state.value=drag.state;paint();}drag=null;if(svg.hasPointerCapture(event.pointerId))svg.releasePointerCapture(event.pointerId);}};
    svg.addEventListener('pointerup',end);svg.addEventListener('pointercancel',end);
    root.querySelector('#map-attribution').innerHTML=`${esc(boundaries.source.attribution)} <a href="${esc(boundaries.source.catalogue_url)}" target="_blank" rel="noopener">Boundary source & licence</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0 attribution</a>. Boundary vintage 2024; crime year ${data.year}. Reference display, not a survey record.`;
    updateView();paint();
  }catch(error){
    if(root.isConnected){stage.replaceChildren();stage.classList.add('map-unavailable');root.querySelector('.crime-table-disclosure').open=true;const message=document.createElement('p');message.setAttribute('role','status');message.textContent=`Geographic map unavailable: ${error.message}. Use the State/UT selector or exact-count table.`;stage.append(message);}
  }
}
