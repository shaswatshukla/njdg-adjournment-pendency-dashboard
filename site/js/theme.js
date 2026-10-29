// Local theme preference, applied before paint without network requests.
let savedTheme=null;
try{savedTheme=localStorage.getItem('jm-theme');}catch{}
document.documentElement.dataset.theme=['light','dark'].includes(savedTheme)?savedTheme:matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
