// Presentation only. Source data and metric definitions remain in their existing modules.
const titles = {overview:'National overview',state:'State explorer',district:'Court coverage',methodology:'Methodology',about:'About this project',health:'Data health',archive:'Snapshot archive',compare:'Compare states',breakdowns:'Data breakdowns',crime:'Crime map','high-courts':'High Courts','supreme-court':'Supreme Court','district-reports':'District reports',reports:'Periodic publications'};

export function setupPresentation() {
  const button=document.getElementById('menu-toggle'), sidebar=document.getElementById('app-sidebar'), backdrop=document.getElementById('nav-backdrop');
  const close=()=>{document.body.classList.remove('nav-open');button.setAttribute('aria-expanded','false');sidebar.inert=matchMedia('(max-width: 980px)').matches;};
  const media=matchMedia('(max-width: 980px)');
  const sync=()=>{sidebar.inert=media.matches&&!document.body.classList.contains('nav-open');};
  media.addEventListener('change',sync);sync();
  button.addEventListener('click',()=>{const open=!document.body.classList.contains('nav-open');document.body.classList.toggle('nav-open',open);button.setAttribute('aria-expanded',String(open));sidebar.inert=!open&&media.matches;if(open)sidebar.querySelector('[aria-current="page"],a')?.focus();});
  backdrop.addEventListener('click',()=>{close();button.focus();});
  sidebar.querySelector('.sidebar-close').addEventListener('click',()=>{close();button.focus();});
  sidebar.addEventListener('click',event=>{if(event.target.closest('a')&&media.matches){close();document.getElementById('main').focus();}});
  document.addEventListener('keydown',event=>{
    if(!document.body.classList.contains('nav-open'))return;
    if(event.key==='Escape'){close();button.focus();}
    if(event.key==='Tab'&&media.matches){const items=[...sidebar.querySelectorAll('a,button,summary')].filter(x=>x.getClientRects().length);const first=items[0],last=items.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}}
  });
  document.querySelector('.skip-link').addEventListener('click',event=>{event.preventDefault();close();document.getElementById('main').focus();});
}

export function polishPresentation(route, mode) {
  document.getElementById('workspace-title').textContent=titles[route]||'Overview';
  document.querySelectorAll('[data-route]').forEach(a=>{if(a.dataset.route===route)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  document.querySelectorAll('nav details').forEach(group=>{if(group.querySelector('[aria-current="page"]'))group.open=true;});
  document.documentElement.dataset.view=route;
  const root=mode==='official'?document.getElementById('official-view'):document.getElementById('view-'+route);
  if(!root)return;
  // One persistent navigation system replaces repeated rows of route chips.
  root.querySelectorAll('.research-nav').forEach(x=>x.remove());
  const actions=root.querySelector('.research-actions');
  actions?.querySelectorAll('a').forEach(x=>x.remove());
  const heading=root.querySelector('.page-heading');
  if(heading&&!heading.parentElement.classList.contains('view-header')){
    const header=document.createElement('div');header.className='view-header';heading.before(header);header.append(heading);
    if(actions)header.append(actions);
    const reportButton=root.querySelector('#research-content > button.button-secondary');
    if(reportButton){const tools=document.createElement('div');tools.className='research-actions';tools.append(reportButton);header.append(tools);}
  }
  root.querySelectorAll('.kpi strong').forEach(x=>{x.classList.toggle('metric-unavailable',x.textContent==='Unavailable');});
  root.querySelectorAll('table').forEach(table=>{table.querySelectorAll('td').forEach(cell=>{if(/^[-+]?\d[\d,.\s]*(?:%| Cr| L)?$/.test(cell.childNodes[0]?.textContent?.trim()||''))cell.classList.add('numeric');});});
  if(mode==='official'&&route==='overview'){
    const heading=root.querySelector('h1');if(heading)heading.textContent='Where the backlog stands.';
    const eyebrow=root.querySelector('.page-heading .eyebrow');if(eyebrow)eyebrow.textContent='INDIA / VERIFIED AGGREGATE REPORTS';
    const chartGrid=root.querySelector('.chart-grid');if(chartGrid)chartGrid.classList.add('overview-grid');
    const table=root.querySelector('#official-level-totals')?.closest('.panel');if(table)table.classList.add('level-panel');
  }
}

