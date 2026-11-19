// Boundary tests for the extension's CDP/download adapter. Real-page DOM tests are separate.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../extension/automation.js'),'utf8');
function harness(debug){
  const context={debug,enabled:true,browserJoined:true,setTimeout,Date,console,URL,
    edgePageTool:function(){},edgeElementTool:function(){}};
  vm.createContext(context);vm.runInContext(source,context);return context;
}
test('ref targets use a backend node and always release their remote object',async()=>{
  const calls=[];const ctx=harness(async(id,method,args)=>{
    calls.push({method,args});if(method==='DOM.resolveNode')return {object:{objectId:'remote-9'}};
    return {};
  });
  await assert.rejects(ctx.withElement(7,{ref:9},()=>{throw Error('fixture');}),/fixture/);
  assert.deepEqual(calls.map(c=>c.method),['DOM.resolveNode','Runtime.releaseObject']);
  assert.equal(calls[0].args.backendNodeId,9);
});
test('AX snapshot exposes role/name/ref, never a textbox value',async()=>{
  const ctx=harness(async()=>({nodes:[{ignored:false,backendDOMNodeId:9,role:{value:'textbox'},
    name:{value:'Name'},value:{value:'private-sentinel'}}]}));
  const data=await ctx.accessibleElements(7);
  assert.equal(data[0].ref,9);assert.equal(data[0].name,'Name');
  assert.ok(!JSON.stringify(data).includes('private-sentinel'));
});
test('waiting only probes and cancellation never performs an action',async()=>{
  let reads=0;const ctx=harness();ctx.evaluate=async()=>({count:1,visible:++reads>1,enabled:true});
  const data=await ctx.waitForElement(7,{selector:'#result',wait_timeout:1});
  assert.equal(data.matched,true);assert.equal(reads,2);
  ctx.enabled=false;await assert.rejects(ctx.waitForElement(7,{selector:'#result'}),/暂停/);
});
test('download streams in the browser frame context without exporting cookies or changing defaults',async()=>{
  const calls=[],messages=[];
  const ctx=harness(async(id,method,args)=>{
    calls.push({method,args});
    if(method==='Page.getFrameTree')return {frameTree:{frame:{id:'frame-1',url:'https://example.test/page'}}};
    if(method==='Network.loadNetworkResource')return {resource:{success:true,httpStatusCode:200,stream:'stream-1',headers:{'content-disposition':'attachment; filename="paper.pdf"'}}};
    if(method==='IO.read')return {data:'AAECAw==',base64Encoded:true,eof:true};
    return {};
  });
  ctx.WebSocket={OPEN:1};ctx.ws={readyState:1,bufferedAmount:0,send:value=>messages.push(JSON.parse(value))};
  ctx.withElement=async(id,args,fn)=>fn('remote');ctx.elementCall=async()=>({href:'https://example.test/paper.pdf',frame_url:'https://example.test/page'});
  const result=await ctx.downloadFile(7,{selector:'#download',directory:'E:/Data',wait_timeout:1,transfer_id:'transfer-1'});
  assert.equal(result.state,'complete');
  assert.equal(calls.find(c=>c.method==='Network.loadNetworkResource').args.options.includeCredentials,true);
  assert.deepEqual(messages.map(m=>m.type),['download_begin','download_chunk']);
  assert.equal(messages[0].filename,'paper.pdf');assert.equal(messages[1].data,'AAECAw==');
  assert.equal(calls.at(-1).method,'IO.close');
  assert.ok(!calls.some(c=>/Cookie|DownloadBehavior/.test(c.method)));
});
