/** Bounded public JSON requests. A slow secondary dataset cannot hold the homepage. */
export async function loadJSON(name, {fetcher=fetch, timeoutMs=12000}={}) {
  const controller=new AbortController();
  let timer;
  try {
    return await Promise.race([
      (async()=>{const response=await fetcher(`./data/${name}.json`,{signal:controller.signal,cache:'no-cache'});if(!response.ok)throw new Error(`${name}: HTTP ${response.status}`);return response.json();})(),
      new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new Error(`${name}: request timed out. Retry or use the published snapshot below.`));},timeoutMs);})
    ]);
  } finally {clearTimeout(timer);}
}
