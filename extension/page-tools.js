function edgeElementTool(op,args={}) {
  const el=this,doc=el.ownerDocument,win=doc.defaultView;
  const visible=el.isConnected&&!!el.getClientRects().length&&win.getComputedStyle(el).visibility!=='hidden';
  const enabled=!el.disabled&&el.getAttribute('aria-disabled')!=='true';
  if(op==='probe')return {count:el.isConnected?1:0,visible,enabled};
  if(op==='download_link'){
    if(el.tagName!=='A'||!el.href||!/^https?:|^blob:/.test(el.href))throw new Error('下载目标必须是页面中实际存在的 HTTP/HTTPS 或 blob 文件链接');
    return {href:el.href,filename:el.download||'',frame_url:doc.URL};
  }
  if(op==='check_file_input'){
    if(el.tagName!=='INPUT'||el.type!=='file')throw new Error('上传目标必须为 input[type=file]');
    if(!enabled)throw new Error('文件输入框已禁用');
    if(args.count>1&&!el.multiple)throw new Error('该输入框只接受一个文件');
    return true;
  }
  if(op==='files')return {uploaded:true,files:Array.from(el.files||[]).map(f=>({name:f.name,size:f.size,type:f.type}))};
  if(!visible)throw new Error('元素不可见；请重新读取页面');
  if(!enabled)throw new Error('元素已禁用');
  el.scrollIntoView({block:'center',inline:'nearest'});
  if(op==='click'){el.click();return {clicked:true};}
  if(op==='select'){
    if(el.tagName!=='SELECT')throw new Error('目标不是下拉框');
    const options=Array.from(el.options).filter(o=>o.value===String(args.value)||o.text.trim()===String(args.value).trim());
    if(options.length!==1)throw new Error('下拉选项不唯一或不存在');
    el.value=options[0].value;
  }else if(op==='fill'){
    if(el.tagName==='INPUT'&&['checkbox','radio'].includes(el.type)){
      const value=['true','1','yes'].includes(String(args.value).toLowerCase());
      if(el.checked!==value)el.click();
      return {filled:true,checked:el.checked};
    }
    if(['INPUT','TEXTAREA'].includes(el.tagName)){
      if(el.readOnly)throw new Error('输入框为只读');
      const proto=el.tagName==='TEXTAREA'?win.HTMLTextAreaElement.prototype:win.HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto,'value').set.call(el,String(args.value));
    }else if(el.isContentEditable){
      el.focus();const range=doc.createRange();range.selectNodeContents(el);
      const selection=win.getSelection();selection.removeAllRanges();selection.addRange(range);
      if(!doc.execCommand('insertText',false,String(args.value)))throw new Error('编辑器不支持标准文本输入');
      return {filled:true};
    }else throw new Error('目标不支持文本填写');
  }else throw new Error('未知元素操作');
  el.dispatchEvent(new win.Event('input',{bubbles:true}));
  el.dispatchEvent(new win.Event('change',{bubbles:true}));
  return {filled:true,value:el.type==='password'?'[已隐藏]':el.value};
}
function edgePageTool(op,args) {
  const norm=v=>String(v||'').replace(/\s+/g,' ').trim();
  const visible=el=>!!el.getClientRects().length&&el.ownerDocument.defaultView.getComputedStyle(el).visibility!=='hidden';
  const text=el=>norm(el.innerText||el.getAttribute('aria-label')||el.title||el.value);
  let doc=document;
  if(args.frame){
    const frames=document.querySelectorAll(args.frame);
    if(frames.length!==1||frames[0].tagName!=='IFRAME')throw new Error('frame 必须唯一定位一个 iframe');
    try{doc=frames[0].contentDocument;}catch(_){doc=null;}
    if(!doc)throw new Error('此 iframe 无法从当前页面读取；请使用快照给出的 ref，或打开对应页面');
  }
  function query(selector){
    let roots=[doc];const parts=selector.split('>>>').map(s=>s.trim());
    for(let i=0;i<parts.length;i++){
      const found=roots.flatMap(root=>Array.from(root.querySelectorAll(parts[i])));
      if(i===parts.length-1)return found;
      roots=found.map(el=>el.shadowRoot).filter(Boolean);
    }
    return [];
  }
  function labels(el){return [...Array.from(el.labels||[]).map(x=>norm(x.innerText)),el.getAttribute('aria-label'),el.getAttribute('placeholder')].filter(Boolean);}
  function resolve(){
    let matches;
    if(args.selector)matches=query(args.selector);
    else if(args.label)matches=query('input,textarea,select,[contenteditable=true]').filter(el=>labels(el).some(l=>l.replace(/\s*[*：:]\s*$/,'')===norm(args.label).replace(/\s*[*：:]\s*$/,'')));
    else if(args.text)matches=query('button,a,[role=button],input[type=submit],input[type=button]').filter(el=>text(el)===norm(args.text));
    else throw new Error('需要 selector、label、text 或 ref');
    return matches;
  }
  if(op==='probe'){
    const matches=resolve();
    if(matches.length!==1)return {count:matches.length,visible:false,enabled:false};
    return edgeElementTool.call(matches[0],'probe');
  }
  if(op==='snapshot'){
    const selector=el=>{
      if(el.id&&doc.querySelectorAll('#'+CSS.escape(el.id)).length===1)return '#'+CSS.escape(el.id);
      const path=[];
      for(let e=el;e&&e!==doc.documentElement;e=e.parentElement){
        const siblings=e.parentElement?Array.from(e.parentElement.children).filter(x=>x.tagName===e.tagName):[e];
        path.unshift(e.tagName.toLowerCase()+(siblings.length>1?':nth-of-type('+(siblings.indexOf(e)+1)+')':''));
        const s=path.join(' > ');if(doc.querySelectorAll(s).length===1)return s;
      }
      return path.join(' > ');
    };
    const fields=Array.from(doc.querySelectorAll('input:not([type=hidden]),textarea,select,[contenteditable=true]')).filter(visible).map(el=>({
      selector:selector(el),tag:el.tagName.toLowerCase(),type:el.type,labels:labels(el),
      // Field values can contain phone numbers, OTPs or private drafts. Opt in explicitly.
      ...(args.include_values?{value:el.type==='password'||el.type==='file'?'[已隐藏]':el.value??el.innerText}:{}),
      checked:el.checked,required:el.required,
      options:el.tagName==='SELECT'?Array.from(el.options).map(o=>({value:o.value,text:o.text})):undefined
    }));
    return {title:doc.title,url:doc.URL,body:(doc.body?.innerText||'').slice(0,Math.min(args.max_length||10000,50000)),fields,
      buttons:Array.from(doc.querySelectorAll('button,[role=button],input[type=submit],input[type=button]')).filter(visible).slice(0,100).map(el=>({selector:selector(el),text:text(el)})),
      links:Array.from(doc.querySelectorAll('a[href]')).filter(visible).slice(0,100).map(el=>({selector:selector(el),text:text(el),url:el.href})),
      frames:Array.from(doc.querySelectorAll('iframe')).map(el=>({title:el.title,url:el.src}))};
  }
  const matches=resolve().filter(el=>op==='resolve'||visible(el));
  if(matches.length!==1)throw new Error('找到 '+matches.length+' 个匹配元素，请提供唯一定位');
  if(op==='resolve')return matches[0];
  return edgeElementTool.call(matches[0],op,args);
}
