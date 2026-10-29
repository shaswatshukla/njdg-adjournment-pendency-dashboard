import { renderOfficialRoute, updateOfficialModeStatus } from './official-mode.js?v=0.7.0';
import { researchRoutes } from './research.js?v=0.7.0';
import { setupPresentation, polishPresentation } from './presentation.js?v=0.7.0';
import { loadJSON } from './data-client.js?v=0.7.0';

const dataset={};
const routes=['overview','state','district','methodology','about',...researchRoutes];
function status(message,kind=''){
  const el=document.querySelector('#official-view .data-status');
  if(el){el.textContent=message;el.className=`data-status ${kind}`;}
}
function showRoute(){
  const requested=location.hash.slice(1).split('?')[0]||'overview';
  const route=routes.includes(requested)?requested:'overview';
  document.title=`Justice Metrics — ${route.replaceAll('-',' ')} — Official reports`;
  document.querySelector('.coverage-short').textContent=dataset.official?.data_as_of||'Unavailable';
  const root=document.getElementById('official-view');
  document.body.classList.remove('crime-map-expanded');
  document.getElementById('crime-map-dialog')?.close();
  try{
    if(!dataset.official?.available){
      if(!dataset.officialError)return;
      document.getElementById('mode-status').textContent='Official reports could not be loaded. No substitute dataset is shown.';
      root.querySelector('.load-error')?.remove();
      const message=document.createElement('div');message.className='alert load-error';message.setAttribute('role','alert');
      const note=document.createElement('p');note.textContent=`Interactive data unavailable: ${dataset.officialError} The dated published summary remains below.`;
      const retry=document.createElement('button');retry.type='button';retry.className='button-secondary';retry.textContent='Retry data loading';retry.addEventListener('click',loadData);
      message.append(note,retry);root.prepend(message);return;
    }
    updateOfficialModeStatus(dataset.official,dataset.refreshStatus,document.getElementById('mode-status'));
    document.documentElement.dataset.interactive='ready';
    renderOfficialRoute(route,dataset.official,dataset.refreshStatus,status,{archive:dataset.archive,crime:dataset.crime,meta:dataset.meta,periodic:dataset.periodic,loadErrors:dataset.loadErrors,secondaryReady:dataset.secondaryReady});
  }catch(error){
    root.replaceChildren();const message=document.createElement('p');message.className='alert';message.setAttribute('role','alert');message.textContent=`Unable to display this view: ${error.message}`;root.append(message);
  }finally{polishPresentation(route,'official');}
}
function setTheme(){
  const root=document.documentElement,button=document.querySelector('.theme-toggle');let saved=null;
  try{saved=localStorage.getItem('jm-theme');}catch{}
  root.dataset.theme=['dark','light'].includes(saved)?saved:matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
  const update=()=>{const dark=root.dataset.theme==='dark';button.setAttribute('aria-pressed',String(dark));button.setAttribute('aria-label',dark?'Switch to light theme':'Switch to dark theme');};
  update();button.addEventListener('click',()=>{root.dataset.theme=root.dataset.theme==='dark'?'light':'dark';try{localStorage.setItem('jm-theme',root.dataset.theme);}catch{}update();showRoute();});
}
async function loadData(){
  dataset.officialError=null;dataset.loadErrors={};dataset.secondaryReady=false;
  const primary=loadJSON('official_snapshot').then(value=>{if(!value.available||!Array.isArray(value.records))throw Error('Official snapshot has no validated records.');dataset.official=value;showRoute();}).catch(error=>{dataset.officialError=error.message;showRoute();});
  const names=['refresh_status','snapshot_archive','crime','periodic_reports','meta'];
  const keys=['refreshStatus','archive','crime','periodic','meta'];
  await Promise.allSettled(names.map(async(name,i)=>{try{dataset[keys[i]]=await loadJSON(name);}catch(error){dataset.loadErrors[name]=error.message;}}));
  dataset.secondaryReady=true;await primary;showRoute();
}
setupPresentation();setTheme();window.addEventListener('hashchange',showRoute);loadData();
document.getElementById('chart-library')?.addEventListener('load',()=>{if(dataset.official)showRoute();});
