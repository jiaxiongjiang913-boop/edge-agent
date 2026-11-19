// Structured CDP operations shared by CLI and MCP. No page credentials are read.
function pageExpression(op,args){
  return '(()=>{const edgeElementTool='+edgeElementTool.toString()+';return ('+edgePageTool.toString()+')('+JSON.stringify(op)+','+JSON.stringify(args)+');})()';
}
async function remoteElement(id,args){
  if(args.ref){
    const result=await debug(id,'DOM.resolveNode',{backendNodeId:Number(args.ref)});
    return result.object.objectId;
  }
  const result=await debug(id,'Runtime.evaluate',{
    expression:pageExpression('resolve',args),
    returnByValue:false,userGesture:true
  });
  if(result.exceptionDetails)throw new Error(result.exceptionDetails.exception?.description||'元素定位失败');
  if(!result.result?.objectId)throw new Error('元素不存在；请重新读取页面');
  return result.result.objectId;
}
async function withElement(id,args,fn){
  const objectId=await remoteElement(id,args);
  try{return await fn(objectId);}finally{await debug(id,'Runtime.releaseObject',{objectId}).catch(()=>{});}
}
async function clickElement(id,args){
  return withElement(id,args,async objectId=>{
    const probe=await elementCall(id,objectId,'probe');
    if(!probe.visible||!probe.enabled)throw new Error('点击目标不可见或已禁用');
    await debug(id,'DOM.scrollIntoViewIfNeeded',{objectId});
    const {quads=[]}=await debug(id,'DOM.getContentQuads',{objectId});
    if(!quads.length)throw new Error('点击目标没有可见区域');
    const q=quads[0],x=(q[0]+q[2]+q[4]+q[6])/4,y=(q[1]+q[3]+q[5]+q[7])/4;
    await debug(id,'Input.dispatchMouseEvent',{type:'mouseMoved',x,y});
    await debug(id,'Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});
    await debug(id,'Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1});
    return {clicked:true};
  });
}
async function elementCall(id,objectId,operation,args={}){
  const result=await debug(id,'Runtime.callFunctionOn',{
    objectId,functionDeclaration:edgeElementTool.toString(),
    arguments:[{value:operation},{value:args}],returnByValue:true,awaitPromise:true,userGesture:true
  });
  if(result.exceptionDetails)throw new Error(result.exceptionDetails.exception?.description||'元素操作失败');
  return result.result?.value??null;
}
async function accessibleElements(id){
  const {nodes=[]}=await debug(id,'Accessibility.getFullAXTree');
  const roles=new Set(['button','link','textbox','searchbox','checkbox','radio','combobox','listbox','option','menuitem','tab','switch','slider','spinbutton']);
  return nodes.filter(n=>!n.ignored&&n.backendDOMNodeId&&roles.has(n.role?.value)).slice(0,250).map(n=>({
    ref:n.backendDOMNodeId,role:n.role.value,name:n.name?.value||'',
    disabled:n.properties?.some(p=>p.name==='disabled'&&p.value?.value===true)||false
  }));
}
async function waitForElement(id,args){
  const state=args.state||'visible',duration=Number(args.wait_timeout??30)*1000;
  if(!['visible','hidden','attached','detached','enabled','ready'].includes(state))throw new Error('不支持的等待状态');
  if(!Number.isFinite(duration)||duration<0||duration>110000)throw new Error('等待时长必须在 0 到 110 秒之间');
  const deadline=Date.now()+duration;
  while(true){
    if(!enabled||!browserJoined)throw new Error('浏览器已暂停；等待已取消');
    let probe;
    if(state==='ready')probe={ready:await evaluate(id,"document.readyState === 'complete'")};
    else if(args.ref){
      try{probe=await withElement(id,args,o=>elementCall(id,o,'probe'));}
      catch(error){
        if(!/No node|not found|does not exist|not belong|detached|Could not find/i.test(error.message))throw error;
        probe={count:0,visible:false,enabled:false};
      }
    }else probe=await evaluate(id,pageExpression('probe',args));
    if(probe.count>1)throw new Error('等待目标不唯一，请先缩小定位');
    const matched=state==='ready'?probe.ready:state==='attached'?probe.count===1:state==='detached'?probe.count===0:
      state==='hidden'?!probe.visible:state==='enabled'?probe.visible&&probe.enabled:probe.visible;
    if(matched)return {matched:true,state,...probe};
    if(Date.now()>=deadline)throw new Error('等待超时：'+state+'；未重放任何点击或填写操作');
    await new Promise(resolve=>setTimeout(resolve,200));
  }
}
async function uploadFiles(id,args){
  if(!Array.isArray(args.files)||!args.files.length)throw new Error('请提供本机文件路径');
  return withElement(id,args,async objectId=>{
    await elementCall(id,objectId,'check_file_input',{count:args.files.length});
    await debug(id,'DOM.setFileInputFiles',{objectId,files:args.files});
    return elementCall(id,objectId,'files');
  });
}
async function downloadFile(id,args){
  if(!args.directory||!args.transfer_id)throw new Error('请通过本机服务指定下载目录');
  const seconds=Number(args.wait_timeout??60);
  if(!Number.isFinite(seconds)||seconds<=0||seconds>110)throw new Error('下载等待时长必须在 0 到 110 秒之间');
  const link=await withElement(id,args,o=>elementCall(id,o,'download_link'));
  if(!/^https?:/.test(link.href))throw new Error('当前流式下载支持 HTTP/HTTPS 文件链接；blob 下载请按网页流程另行处理');
  const {frameTree}=await debug(id,'Page.getFrameTree');
  function findFrame(tree){
    if(tree.frame.url===link.frame_url)return tree.frame.id;
    for(const child of tree.childFrames||[]){const found=findFrame(child);if(found)return found;}
    return null;
  }
  const frameId=findFrame(frameTree);
  if(!frameId)throw new Error('无法确定文件链接所在的页面，请重新读取快照');
  const socket=ws,deadline=Date.now()+seconds*1000;
  const send=async message=>{
    if(!enabled||!browserJoined||ws!==socket||socket?.readyState!==WebSocket.OPEN)throw new Error('浏览器已暂停或连接改变，下载已取消');
    if(Date.now()>deadline)throw new Error('下载等待超时；未重复请求。下载 ID '+args.transfer_id);
    while(socket.bufferedAmount>1024*1024){
      await new Promise(resolve=>setTimeout(resolve,25));
      if(Date.now()>deadline||ws!==socket||socket.readyState!==WebSocket.OPEN)throw new Error('本地文件传输等待超时或已断开');
    }
    socket.send(JSON.stringify({...message,id:args.transfer_id}));
  };
  let stream;
  try{
    // Read the observed link in its browser frame's network context. Authentication
    // stays in Edge; no cookies or authorization headers leave the browser.
    const {resource}=await debug(id,'Network.loadNetworkResource',{
      frameId,url:link.href,options:{disableCache:false,includeCredentials:true}
    });
    stream=resource.stream;
    if(!resource.success||!stream||resource.httpStatusCode>=400)throw new Error('文件请求失败，HTTP '+resource.httpStatusCode+'；'+(resource.netErrorName||'未返回文件流'));
    const headers=Object.fromEntries(Object.entries(resource.headers||{}).map(([k,v])=>[k.toLowerCase(),String(v)]));
    const disposition=headers['content-disposition']||'';
    const utf=disposition.match(/filename\*=UTF-8''([^;]+)/i),plain=disposition.match(/filename="?([^";]+)"?/i);
    let filename=link.filename||new URL(link.href).pathname.split('/').pop()||'download.bin';
    try{if(utf)filename=decodeURIComponent(utf[1]);else if(plain)filename=plain[1];else filename=decodeURIComponent(filename);}catch(_){}
    if(/\.pdf$/i.test(filename)&&/text\/html/i.test(headers['content-type']||''))throw new Error('文件链接返回了 HTML 页面，可能需要登录；未保存为 PDF');
    await send({type:'download_begin',filename});
    while(true){
      const chunk=await debug(id,'IO.read',{handle:stream,size:65536});
      if(chunk.data)await send({type:'download_chunk',data:chunk.data,base64:chunk.base64Encoded===true});
      if(chunk.eof)break;
    }
    return {state:'complete',http_status:resource.httpStatusCode};
  }finally{
    if(stream)await debug(id,'IO.close',{handle:stream}).catch(()=>{});
  }
}
