const $ = id => document.getElementById(id);
async function action(type, extra={}) {
  const result=await chrome.runtime.sendMessage({type,...extra});
  if(!result?.ok)throw new Error(result?.error||'扩展暂未响应');
  return result;
}
async function refresh() {
  try {
    const s=await action('status');
    $('status').textContent=!s.enabled?'连接已暂停':s.connected?'本地服务已连接':'等待本地服务';
    $('badge').textContent=!s.enabled?'已暂停':s.connected?'已连接':'未连接';
    $('description').textContent=s.connected?`整个浏览器已接入，共 ${s.tabs.length} 个标签页。`:'请双击 Start.cmd 启动本地服务，然后点击工具栏扩展图标。';
    $('resume').disabled=s.connected&&s.enabled;$('pause').disabled=!s.enabled;
    $('tabs').replaceChildren();
    if(!s.tabs.length)$('tabs').textContent='点击“恢复连接”接入整个浏览器。';
    for(const t of s.tabs) {
      const row=document.createElement('div');row.className='tab';
      const title=document.createElement('strong');title.textContent=`${t.id} · ${t.title||'无标题'}`;
      const url=document.createElement('p');url.textContent=t.url;
      const button=document.createElement('button');button.className='secondary';button.textContent=t.active?'当前标签页':'切换到此标签页';button.disabled=t.active;
      button.onclick=()=>run('activate',{tabId:t.id});row.append(title,url,button);$('tabs').append(row);
    }
  } catch(e){$('error').textContent=e.message;}
}
async function run(type,extra={}) {
  try{$('error').textContent='';await action(type,extra);await refresh();}
  catch(e){$('error').textContent=e.message;}
}
$('pause').onclick=()=>run('pause');$('resume').onclick=()=>run('resume');refresh();setInterval(refresh,2500);
