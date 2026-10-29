import {renderOfficialRoute,updateOfficialModeStatus} from './official-mode.js?v=0.8.0';
import {researchRoutes,renderResearch} from './research.js?v=0.8.0';
import {setupPresentation,polishPresentation} from './presentation.js?v=0.8.0';
import {loadJSON,createDataStore,requirementsFor} from './data-client.js?v=0.8.0';
const data=createDataStore(loadJSON);
const bootstrap=JSON.parse(document.getElementById('data-bootstrap')?.textContent||'{}');
const routes=['overview','state','district','methodology','about',...researchRoutes];
const keys={official_snapshot:'official',refresh_status:'refreshStatus',snapshot_archive:'archive',crime:'crime',periodic_reports:'periodic',meta:'meta'};
let navigation=0;
function currentRoute(){const name=location.hash.slice(1).split('?')[0]||'overview';return routes.includes(name)?name:'overview';}
function status(message,kind=''){const el=document.querySelector('#official-view .data-status');if(el){el.textContent=message;el.className=`data-status ${kind}`;}}
function updateBanner(){const snapshot=data.peek('official_snapshot')||bootstrap.reference;if(snapshot)updateOfficialModeStatus(snapshot,data.peek('refresh_status'),document.getElementById('mode-status'));}
function errorNotice(root,route,errors){
  root.querySelector('.load-error')?.remove();const box=document.createElement('section');box.className='panel load-error';box.setAttribute('role','alert');
  const heading=document.createElement('h1');heading.textContent='Interactive data unavailable';
  const p=document.createElement('p');p.textContent=errors.join(' ')+' Dated evidence pages remain available.';
  const retry=document.createElement('button');retry.className='button-secondary';retry.type='button';retry.textContent='Retry this view';retry.addEventListener('click',()=>showRoute({force:true}));
  const link=document.createElement('a');link.href='sources/';link.textContent='Read sources and reporting dates';box.append(heading,p,retry,document.createTextNode(' '),link);
  if(route==='overview'){heading.remove();root.prepend(box);}else root.replaceChildren(box);
}
async function showRoute({force=false,focus=false}={}){
  const run=++navigation,route=currentRoute(),root=document.getElementById('official-view');
  document.title=`${({overview:'Court pendency in India',state:'State and UT court pendency',crime:'Registered crime in India — separate context',health:'Sources and data status'})[route]||route.replaceAll('-',' ')} | Justice Metrics`;
  root.setAttribute('aria-busy','true');document.getElementById('navigation-status').textContent='Loading '+route.replaceAll('-',' ')+'.';
  const needed=requirementsFor(route);if(force)needed.forEach(name=>data.invalidate(name));
  const results=await Promise.allSettled(needed.map(name=>data.get(name)));if(run!==navigation)return;
  document.getElementById('crime-map-dialog')?.close();document.body.classList.remove('crime-map-expanded');Object.values(window.Chart?.instances||{}).forEach(chart=>chart.destroy());
  const errors=results.flatMap((r,i)=>r.status==='rejected'?[`${needed[i]}: ${r.reason.message}`]:[]),snapshot=data.peek('official_snapshot');
  const fatal=route==='crime'?!data.peek('crime'):['district-reports','reports'].includes(route)?!data.peek('periodic_reports'):!snapshot?.available;
  try{
    if(fatal){errorNotice(root,route,errors);return;}
    const extras={loadErrors:data.errors(),secondaryReady:true,districtCoverageRows:bootstrap.districtCoverageRows||[]};for(const [name,key] of Object.entries(keys))extras[key]=data.peek(name);
    if(['crime','district-reports','reports'].includes(route))renderResearch(route,snapshot||bootstrap.reference,data.peek('refresh_status'),extras,root);
    else renderOfficialRoute(route,snapshot,data.peek('refresh_status'),status,extras);
    if(errors.length){const p=document.createElement('p');p.className='alert';p.textContent='Supporting data unavailable: '+errors.join(' ');root.prepend(p);}
    document.documentElement.dataset.interactive='ready';document.querySelector('.coverage-short').textContent=(snapshot||bootstrap.reference)?.data_as_of||'See reporting dates';updateBanner();
  }catch(error){errorNotice(root,route,[error.message]);}
  finally{root.setAttribute('aria-busy','false');polishPresentation(route,'official');document.getElementById('navigation-status').textContent=route.replaceAll('-',' ')+' view ready.';if(focus){const h=root.querySelector('h1');if(h){h.tabIndex=-1;h.focus();}}}
}
function setupTheme(){
  const button=document.querySelector('.theme-toggle');const update=()=>{const dark=document.documentElement.dataset.theme==='dark';button.setAttribute('aria-pressed',String(dark));button.setAttribute('aria-label',dark?'Switch to light theme':'Switch to dark theme');};update();
  button.addEventListener('click',()=>{
    const tokens=['--chart-pending','--chart-clearance','--chart-adjournment','--chart-compare','--chart-flow','--chart-grid','--chart-text','--gold'];const before=getComputedStyle(document.documentElement),old=tokens.map(t=>before.getPropertyValue(t).trim());
    document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';try{localStorage.setItem('jm-theme',document.documentElement.dataset.theme);}catch{}
    const after=getComputedStyle(document.documentElement),colours=new Map(tokens.map((t,i)=>[old[i],after.getPropertyValue(t).trim()]));const colour=v=>Array.isArray(v)?v.map(colour):colours.get(v)||v;
    for(const chart of Object.values(window.Chart?.instances||{})){
      for(const set of chart.data.datasets)for(const key of ['borderColor','backgroundColor','pointBackgroundColor'])if(set[key])set[key]=colour(set[key]);
      for(const scale of Object.values(chart.options.scales||{})){if(scale.ticks)scale.ticks.color=after.getPropertyValue('--chart-text').trim();if(scale.grid)scale.grid.color=after.getPropertyValue('--chart-grid').trim();}
      if(chart.options.plugins?.legend?.labels)chart.options.plugins.legend.labels.color=after.getPropertyValue('--chart-text').trim();chart.update('none');
    }update();
  });
}
setupPresentation();setupTheme();window.addEventListener('hashchange',()=>showRoute({focus:true}));showRoute();
// This small freshness request updates only the banner, never rebuilds a view.
data.get('refresh_status').then(updateBanner).catch(()=>{});
