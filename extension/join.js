const $=id=>document.getElementById(id);
let phase='initial',busy=false;
async function message(type){const v=await chrome.runtime.sendMessage({type});if(!v?.ok)throw new Error(v?.error||'扩展暂未响应');return v;}
function setPhase(next,title,detail){
  phase=next;document.body.dataset.phase=next;
  $('join-status').textContent=title;$('join-detail').textContent=detail;
  $('retry').hidden=!['paused','error'].includes(next);
  $('pause').hidden=['paused','error'].includes(next);
  $('manage').disabled=next==='connecting'||next==='initial';
}
function display(s){
  $('count').textContent=String(s.tabs.length);
  if(s.browser_scope&&s.connected&&s.enabled){
    setPhase('connected','浏览器已连接','Agent 可控制此浏览器的全部标签页。');
    $('join-badge').textContent='已连接';$('join-error').textContent='';
  }else if(!s.enabled){
    setPhase('paused','浏览器连接已暂停','点击“重新接入”后恢复连接。');
    $('join-badge').textContent='已暂停';$('join-error').textContent='';
  }else if(!busy){
    setPhase('error','暂未连接',s.lastError||'点击“重新接入”，自动启动本地服务。');
    $('join-badge').textContent='未连接';
  }
}
async function join(explicit=false){
  if(busy)return;busy=true;$('join-error').textContent='';
  try{
    const s=await message('status');
    if((!s.enabled&&!explicit)||(s.connected&&s.browser_scope&&s.enabled)){display(s);return;}
    setPhase('connecting','正在连接浏览器','正在自动启动本地服务，请稍候。');$('join-badge').textContent='连接中';
    await message('connectBrowser');display(await message('status'));
  }catch(error){
    setPhase('error','暂时无法连接',error.message);
    $('join-badge').textContent='未连接';$('join-error').textContent=error.message;
  }finally{busy=false;}
}
async function initialize(){
  const manifest=chrome.runtime.getManifest();
  if(!manifest.permissions?.includes('nativeMessaging')){
    const saved=await chrome.storage.local.get('autoUpgradeAttemptedAt');
    if(saved.autoUpgradeAttemptedAt&&Date.now()-saved.autoUpgradeAttemptedAt<30000){
      setPhase('error','扩展更新尚未完成','请在扩展管理页重新加载 Edge Agent。');return;
    }
    setPhase('connecting','正在更新连接组件','更新后将自动继续连接。');
    await chrome.storage.local.set({autoUpgradeAttemptedAt:Date.now(),reopenAfterUpgrade:Date.now()});
    chrome.runtime.reload();return;
  }
  await chrome.storage.local.remove('autoUpgradeAttemptedAt');
  await join();
  setInterval(()=>{if(!busy)message('status').then(display).catch(()=>{});},2000);
}
$('retry').onclick=()=>join(true);
$('manage').onclick=()=>chrome.runtime.openOptionsPage();
$('pause').onclick=async()=>{try{await message('pause');display(await message('status'));}catch(e){$('join-error').textContent=e.message;}};
initialize().catch(error=>{setPhase('error','暂时无法连接',error.message);$('join-badge').textContent='未连接';});
