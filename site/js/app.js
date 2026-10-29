import { renderOfficialRoute, updateOfficialModeStatus } from './official-mode.js?v=0.6.0';
import { researchRoutes } from './research.js?v=0.6.0';
import { setupPresentation, polishPresentation } from './presentation.js?v=0.6.0';

const dataset={};
const routes=['overview','state','district','methodology','about',...researchRoutes];
function status(message,kind=''){
  const el=document.querySelector('#official-view .data-status');
  if(el){el.textContent=message;el.className=`data-status ${kind}`;}
}
async function getJSON(name){
  const response=await fetch(`./data/${name}.json`);
  if(!response.ok)throw new Error(`${name} unavailable (HTTP ${response.status})`);
  return response.json();
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
      document.getElementById('mode-status').textContent='Official reports could not be loaded. No substitute dataset is shown.';
      root.replaceChildren();
      const heading=document.createElement('h1');heading.textContent='Official data unavailable';
      const message=document.createElement('p');message.className='alert';message.textContent=dataset.officialError||'The verified source could not be loaded. No replacement figures are shown.';
      root.append(heading,message);return;
    }
    updateOfficialModeStatus(dataset.official,dataset.refreshStatus,document.getElementById('mode-status'));
    renderOfficialRoute(route,dataset.official,dataset.refreshStatus,status,{archive:dataset.archive,crime:dataset.crime,meta:dataset.meta,periodic:dataset.periodic});
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
async function start(){
  setupPresentation();setTheme();window.addEventListener('hashchange',showRoute);
  const names=['official_snapshot','refresh_status','snapshot_archive','crime','periodic_reports','meta'];
  const results=await Promise.allSettled(names.map(getJSON));
  const keys=['official','refreshStatus','archive','crime','periodic','meta'];
  results.forEach((r,i)=>{if(r.status==='fulfilled')dataset[keys[i]]=r.value;else if(i===0)dataset.officialError=r.reason.message;});
  showRoute();
}
start();
