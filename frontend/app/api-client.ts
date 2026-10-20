// Shared same-origin client. Staff CSRF tokens never enter URLs or logs.
export function apiFetch(input:RequestInfo|URL,init:RequestInit={}){
 const headers=new Headers(init.headers);
 if(!['GET','HEAD','OPTIONS'].includes((init.method||'GET').toUpperCase())&&typeof document!=='undefined'){
  const cookie=document.cookie.split('; ').find(value=>value.startsWith('renal_csrf='));
  if(cookie)headers.set('X-CSRF-Token',decodeURIComponent(cookie.slice('renal_csrf='.length)));
 }
 return fetch(input,{credentials:'include',...init,headers});
}
