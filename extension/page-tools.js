function edgePageTool(op, args) {
  const norm = v => String(v || '').replace(/\s+/g, ' ').trim();
  const cleanLabel = v => norm(v).replace(/\s*[*：:]\s*$/, '');
  const visible = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
  const labels = el => [...Array.from(el.labels || []).map(x => norm(x.innerText)), el.getAttribute('aria-label'), el.getAttribute('placeholder')].filter(Boolean);
  const selector = el => {
    if (el.id) return '#' + CSS.escape(el.id);
    if (el.getAttribute('name')) {
      const s = el.tagName.toLowerCase() + '[name=' + JSON.stringify(el.getAttribute('name')) + ']';
      if (document.querySelectorAll(s).length === 1) return s;
    }
    const path = [];
    for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
      const siblings = e.parentElement ? Array.from(e.parentElement.children).filter(x => x.tagName === e.tagName) : [e];
      path.unshift(e.tagName.toLowerCase() + (siblings.length > 1 ? ':nth-of-type(' + (siblings.indexOf(e) + 1) + ')' : ''));
      const s = path.join(' > '); if (document.querySelectorAll(s).length === 1) return s;
    }
    return path.join(' > ');
  };
  const text = el => norm(el.innerText || el.value || el.getAttribute('aria-label') || el.title);
  const resolve = () => {
    let matches;
    if (args.selector) matches = Array.from(document.querySelectorAll(args.selector));
    else if (args.label) matches = Array.from(document.querySelectorAll('input,textarea,select,[contenteditable=true]')).filter(el => labels(el).some(l => cleanLabel(l) === cleanLabel(args.label)));
    else if (args.text) matches = Array.from(document.querySelectorAll('button,a,[role=button],input[type=submit],input[type=button]')).filter(el => text(el) === norm(args.text));
    else throw new Error('需要 selector、label 或 text');
    matches = matches.filter(visible);
    if (matches.length !== 1) throw new Error('找到 ' + matches.length + ' 个匹配元素，请提供唯一定位');
    return matches[0];
  };
  if (op === 'snapshot') {
    const fields = Array.from(document.querySelectorAll('input:not([type=hidden]),textarea,select')).filter(visible).map(el => ({
      selector: selector(el), tag: el.tagName.toLowerCase(), type: el.type, labels: labels(el), id: el.id, name: el.name,
      value: el.type === 'password' ? '[已隐藏]' : el.value, checked: el.checked, required: el.required,
      options: el.tagName === 'SELECT' ? Array.from(el.options).map(o => ({value:o.value,text:o.text})) : undefined
    }));
    return {title:document.title,url:location.href,body:document.body.innerText.slice(0, Math.min(args.max_length || 10000, 50000)),fields,
      buttons:Array.from(document.querySelectorAll('button,[role=button],input[type=submit],input[type=button]')).filter(visible).slice(0,100).map(el=>({selector:selector(el),text:text(el)})),
      links:Array.from(document.querySelectorAll('a[href]')).filter(visible).slice(0,100).map(el=>({selector:selector(el),text:text(el),url:el.href})),
      frames:Array.from(document.querySelectorAll('iframe')).map(el=>({title:el.title,url:el.src}))};
  }
  const el = resolve();
  el.scrollIntoView({block:'center',inline:'nearest'});
  if (op === 'click') { el.click(); return {clicked:true,selector:selector(el)}; }
  if (op === 'select') {
    if (el.tagName !== 'SELECT') throw new Error('目标不是下拉框');
    const options = Array.from(el.options).filter(o=>o.value === String(args.value) || norm(o.text) === norm(args.value));
    if (options.length !== 1) throw new Error('下拉选项不唯一或不存在');
    el.value = options[0].value;
  } else if (op === 'fill') {
    if (el instanceof HTMLInputElement && ['checkbox','radio'].includes(el.type)) {
      const value = ['true','1','yes'].includes(String(args.value).toLowerCase());
      if (el.checked !== value) el.click();
      return {filled:true,checked:el.checked};
    }
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
      const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto,'value').set.call(el,String(args.value));
    } else if (el.isContentEditable) el.textContent = String(args.value);
    else throw new Error('目标不支持文本填写');
  } else throw new Error('未知页面命令');
  el.dispatchEvent(new Event('input',{bubbles:true}));
  el.dispatchEvent(new Event('change',{bubbles:true}));
  return {filled:true,selector:selector(el),value:el.type==='password'?'[已隐藏]':el.value};
}
