/** Bounded public JSON requests. A slow secondary dataset cannot hold the homepage. */
export async function loadJSON(name, {fetcher=fetch, timeoutMs=12000, url=`./data/${name}.json`}={}) {
  const controller=new AbortController();
  let timer;
  try {
    return await Promise.race([
      (async()=>{const response=await fetcher(url,{signal:controller.signal,cache:'no-cache'});if(!response.ok)throw new Error(`${name}: HTTP ${response.status}`);return response.json();})(),
      new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new Error(`${name}: request timed out. Retry or use the published snapshot below.`));},timeoutMs);})
    ]);
  } finally {clearTimeout(timer);}
}

export function requirementsFor(route){
  if(route==='crime')return ['crime'];
  if(['district-reports','reports'].includes(route))return ['periodic_reports'];
  if(route==='supreme-court')return ['official_snapshot','periodic_reports'];
  if(route==='archive')return ['official_snapshot','snapshot_archive'];
  if(route==='health')return ['official_snapshot','meta','refresh_status'];
  return ['official_snapshot'];
}

/** Cache requests in memory; failed requests can be retried without fetching other views. */
export function createDataStore(loader){
  const values=new Map(),pending=new Map(),failures=new Map();
  return {peek:name=>values.get(name),errors:()=>Object.fromEntries(failures),
    invalidate(name){values.delete(name);pending.delete(name);failures.delete(name);},
    get(name){
      if(values.has(name))return Promise.resolve(values.get(name));if(pending.has(name))return pending.get(name);
      const request=Promise.resolve().then(()=>loader(name)).then(value=>{values.set(name,value);failures.delete(name);return value;}).catch(error=>{failures.set(name,error.message);throw error;}).finally(()=>pending.delete(name));pending.set(name,request);return request;
    }
  };
}
