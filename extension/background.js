importScripts('page-tools.js');
let enabled=true,browserJoined=false,authenticated=false,ws=null,keepalive=null,reconnectTimer=null;
let reconnectDelay=1000,config=null,lastError='',connecting=null,pausing=false;
let nativeStarting=null,joining=null,joinGeneration=0;
const tabs=new Map(),attached=new Set(),queues=new Map();
const alarmName='edge-agent-reconnect';
const normalURL=url=>/^https?:\/\//.test(url||'');
const debug=(id,method,params={})=>chrome.debugger.sendCommand({tabId:id},method,params);
function state(){return {type:'state',enabled,browser_scope:browserJoined,tabs:Array.from(tabs.values())};}
function sendState(){if(authenticated&&ws?.readyState===WebSocket.OPEN)ws.send(JSON.stringify(state()));}
async function updateBadges(){
  const text=!browserJoined?'':!enabled?'Ⅱ':authenticated?'ON':'…';
  const title=!browserJoined?'点击，接入整个 Edge 浏览器':!enabled?'Edge Agent · 整个浏览器已暂停':authenticated?'Edge Agent · 整个浏览器已接入':'Edge Agent · 正在连接本地服务';
  await chrome.action.setBadgeText({text});await chrome.action.setTitle({title});
  await chrome.action.setBadgeBackgroundColor({color:authenticated?'#12805c':'#a96616'});
  for(const id of tabs.keys()){
    try{await chrome.action.setBadgeText({tabId:id,text});await chrome.action.setTitle({tabId:id,title});}catch(_){}
  }
}
async function refreshTabs(){
  const next=new Map();
  if(browserJoined)for(const t of await chrome.tabs.query({}))next.set(t.id,{id:t.id,title:t.title||'',url:t.url||'',windowId:t.windowId,index:t.index,active:!!t.active,controllable:normalURL(t.url)});
  tabs.clear();for(const [id,t] of next)tabs.set(id,t);
  sendState();await updateBadges();
}
function clearReconnect(){if(reconnectTimer)clearTimeout(reconnectTimer);reconnectTimer=null;chrome.alarms.clear(alarmName);}
function scheduleReconnect(){
  if(!enabled||!browserJoined||reconnectTimer)return;
  chrome.alarms.create(alarmName,{delayInMinutes:.5});
  reconnectTimer=setTimeout(()=>{reconnectTimer=null;connect().catch(()=>{});},reconnectDelay);
  reconnectDelay=Math.min(reconnectDelay*2,15000);
}
async function connect(){
  if(!enabled||!browserJoined)return;
  if(authenticated&&ws?.readyState===WebSocket.OPEN)return;
  if(connecting)return connecting;
  connecting=new Promise(async(resolve,reject)=>{
    let timer,settled=false;
    const finish=error=>{if(settled)return;settled=true;clearTimeout(timer);error?reject(error):resolve();};
    try{
      if(!config){
        const response=await fetch(chrome.runtime.getURL('connection.json'),{cache:'no-store'});
        if(!response.ok)throw new Error('点击扩展图标可自动启动本地服务');
        config=await response.json();
        if(config.url!=='ws://127.0.0.1:18765/ws'||typeof config.token!=='string')throw new Error('本地连接配置无效');
      }
      const socketConfig=config;const socket=new WebSocket(socketConfig.url);ws=socket;
      timer=setTimeout(()=>{finish(new Error('本地服务未响应，请点击重新接入'));socket.close();},8000);
      socket.onopen=()=>{if(!enabled||!browserJoined){socket.close();return;}socket.send(JSON.stringify({type:'auth',token:socketConfig.token}));};
      socket.onmessage=event=>{
        if(ws!==socket)return;
        let data;try{data=JSON.parse(event.data);}catch(_){return;}
        if(data.type==='welcome'){
          if(!enabled||!browserJoined){socket.close();return;}
          authenticated=true;lastError='';reconnectDelay=1000;clearReconnect();
          if(keepalive)clearInterval(keepalive);
          keepalive=setInterval(()=>{if(ws===socket&&socket.readyState===WebSocket.OPEN)socket.send(JSON.stringify({type:'ping'}));},20000);
          refreshTabs();finish();
        }else if(data.type==='command'&&authenticated)enqueue(data,socket);
      };
      socket.onerror=()=>{lastError='本地服务未连接，点击扩展可自动启动';};
      socket.onclose=()=>{
        if(ws!==socket)return;
        ws=null;authenticated=false;if(keepalive)clearInterval(keepalive);keepalive=null;
        finish(new Error(lastError||'连接已断开'));updateBadges();scheduleReconnect();
      };
    }catch(error){lastError=error.message;finish(error);scheduleReconnect();}
  });
  try{await connecting;}finally{connecting=null;}
}
async function ensureNativeService(){
  if(!nativeStarting){
    nativeStarting=(async()=>{
      let result;
      try{result=await chrome.runtime.sendNativeMessage('com.edge_agent.launcher',{action:'ensure_service'});}
      catch(error){throw new Error('本机启动组件未响应：'+error.message);}
      if(!result?.ok||result.app!=='EdgeAgent')throw new Error(result?.error||'本地服务未能启动，请重试');
      config=null;return result;
    })().finally(()=>{nativeStarting=null;});
  }
  return nativeStarting;
}
async function connectBrowser(){
  if(joining)return joining;
  const generation=++joinGeneration;
  joining=(async()=>{
    browserJoined=true;enabled=true;
    await chrome.storage.local.set({enabled:true,browserJoined:true});
    await refreshTabs();await ensureNativeService();
    if(!enabled||generation!==joinGeneration)return {paused:true};
    if(connecting){try{await connecting;}catch(_){}}
    if(!enabled||generation!==joinGeneration)return {paused:true};
    await connect();sendState();await updateBadges();
    return {connected:authenticated,browser_scope:true,tabCount:tabs.size};
  })().catch(error=>{lastError=error.message;throw error;}).finally(()=>{joining=null;});
  return joining;
}
async function pause(){
  ++joinGeneration;enabled=false;await chrome.storage.local.set({enabled:false});clearReconnect();
  if(keepalive)clearInterval(keepalive);keepalive=null;
  const socket=ws;ws=null;authenticated=false;if(socket)socket.close();
  pausing=true;
  for(const id of attached){try{await chrome.debugger.detach({tabId:id});}catch(_){}}
  attached.clear();pausing=false;await updateBadges();return {paused:true};
}
async function ensureAttached(id){
  try{await debug(id,'Runtime.evaluate',{expression:'1',returnByValue:true});}
  catch(_){await chrome.debugger.attach({tabId:id},'1.3');}
  attached.add(id);
}
async function evaluate(id,expression){
  const result=await debug(id,'Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});
  if(result.exceptionDetails)throw new Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text||'页面脚本执行失败');
  return result.result?.value??null;
}
async function execute(id,op,args){
  if(op==='new_tab'){
    const url=args.url||'about:blank';if(!normalURL(url)&&url!=='about:blank')throw new Error('新建标签仅支持普通网页或空白页');
    const t=await chrome.tabs.create({url,active:args.active!==false});await refreshTabs();
    return {id:t.id,url:t.url||url,windowId:t.windowId};
  }
  if(!tabs.has(id))throw new Error('该标签页不在当前浏览器中');
  if(op==='activate'){
    const t=await chrome.tabs.update(id,{active:true});await chrome.windows.update(t.windowId,{focused:true});await refreshTabs();return {active:true,id};
  }
  if(op==='close_tab'){await chrome.tabs.remove(id);await refreshTabs();return {closed:true,id};}
  const tab=await chrome.tabs.get(id);
  if(!normalURL(tab.url))throw new Error('浏览器已接入，但此内部页面不支持网页脚本；可以切换、新建或关闭标签页');
  await ensureAttached(id);
  if(op==='eval')return evaluate(id,String(args.expression));
  if(op==='screenshot')return debug(id,'Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  if(op==='navigate'){
    if(!normalURL(args.url))throw new Error('仅支持 http/https 地址');
    return debug(id,'Page.navigate',{url:args.url});
  }
  if(!['snapshot','fill','select','click'].includes(op))throw new Error('不支持的命令');
  return evaluate(id,'('+edgePageTool.toString()+')('+JSON.stringify(op)+','+JSON.stringify(args)+')');
}
function enqueue(message,socket){
  const id=message.tab_id,previous=queues.get(id)||Promise.resolve();
  const work=previous.catch(()=>{}).then(async()=>{
    try{
      if(ws!==socket||!authenticated||!enabled||!browserJoined)throw new Error('浏览器连接已变化，未执行排队命令');
      const result=await execute(id,message.op,message.args||{});
      if(ws===socket&&socket.readyState===WebSocket.OPEN)socket.send(JSON.stringify({type:'result',id:message.id,ok:true,result}));
    }catch(error){if(ws===socket&&socket.readyState===WebSocket.OPEN)socket.send(JSON.stringify({type:'result',id:message.id,ok:false,error:error.message}));}
  });
  queues.set(id,work);work.finally(()=>{if(queues.get(id)===work)queues.delete(id);});
}
chrome.debugger.onDetach.addListener((source,reason)=>{
  attached.delete(source.tabId);
  if(reason==='canceled_by_user'&&!pausing&&enabled)pause();
});
for(const event of [chrome.tabs.onCreated,chrome.tabs.onUpdated,chrome.tabs.onRemoved,chrome.tabs.onActivated,chrome.tabs.onAttached,chrome.tabs.onDetached]){
  event.addListener(()=>{if(browserJoined)refreshTabs().catch(()=>{});});
}
chrome.alarms.onAlarm.addListener(alarm=>{if(alarm.name===alarmName&&enabled)connect().catch(()=>{});});
chrome.contextMenus.onClicked.addListener(info=>{
  if(info.menuItemId==='manage')chrome.runtime.openOptionsPage();
  if(info.menuItemId==='pause')ready.then(pause);
});
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
  if(sender.id!==chrome.runtime.id)return false;
  ready.then(async()=>{
    if(message.type==='status')return {connected:authenticated,enabled,browser_scope:browserJoined,tabs:Array.from(tabs.values()),lastError};
    if(['connectBrowser','resume'].includes(message.type))return connectBrowser();
    if(message.type==='pause')return pause();
    if(message.type==='activate')return execute(Number(message.tabId),'activate',{});
    throw new Error('未知管理操作');
  }).then(result=>reply({ok:true,...result}),error=>reply({ok:false,error:error.message}));
  return true;
});
const ready=(async()=>{
  const saved=await chrome.storage.local.get({enabled:true,browserJoined:false,reopenAfterUpgrade:0});enabled=saved.enabled;browserJoined=saved.browserJoined;
  await chrome.contextMenus.removeAll();
  chrome.contextMenus.create({id:'manage',title:'管理浏览器连接',contexts:['action']});
  chrome.contextMenus.create({id:'pause',title:'暂停整个浏览器连接',contexts:['action']});
  await refreshTabs();if(enabled&&browserJoined)connect().catch(()=>{});
  if(saved.reopenAfterUpgrade){
    await chrome.storage.local.remove('reopenAfterUpgrade');
    if(Date.now()-Number(saved.reopenAfterUpgrade)<120000){
      setTimeout(()=>{
        if(enabled)connectBrowser().catch(()=>{});
        chrome.action.openPopup().catch(()=>{});
      },0);
    }
  }
})();
