(() => {
  const token = __TOKEN__;
  const product = __PRODUCT_ROOT__;
  const folder = product + '\\extension';
  const $ = id => document.getElementById(id);
  $('folder').textContent = folder;
  async function api(path, method = 'GET') {
    const response = await fetch(path, {method, headers: {Authorization: 'Bearer ' + token}});
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }
  async function refresh() {
    try {
      const data = await api('/api/status');
      $('state').textContent = data.connected && data.browser_scope ? '浏览器已接入' : '等待接入';
      $('state').className = 'badge' + (data.connected ? ' ok' : '');
      $('detail').textContent = `浏览器共 ${data.tabs.length} 个标签页 · 服务运行 ${data.uptime} 秒`;
      $('tabs').replaceChildren();
      if (!data.tabs.length) $('tabs').textContent = '点击扩展图标，即可接入整个浏览器。';
      for (const tab of data.tabs) {
        const item = document.createElement('div'); item.className = 'tab';
        const title = document.createElement('strong'); title.textContent = `${tab.id} · ${tab.title || '无标题'}`;
        const url = document.createElement('small'); url.textContent = tab.url;
        item.append(title, url); $('tabs').append(item);
      }
      $('error').textContent = '';
    } catch (_) { $('state').textContent = '服务已停止'; $('state').className = 'badge'; $('error').textContent = '需要再次启动时，请双击 Start.cmd。'; }
  }
  $('copy').onclick = async () => {await navigator.clipboard.writeText(folder); $('copy').textContent = '已复制';};
  $('extensions').onclick = async () => {await navigator.clipboard.writeText('edge://extensions'); $('extensions').textContent = '已复制 edge://extensions，请粘贴到地址栏';};
  $('refresh').onclick = refresh;
  $('stop').onclick = async () => {if (confirm('停止本地服务？浏览器和网页会保持打开。')) {await api('/api/shutdown', 'POST'); setTimeout(refresh, 600);}};
  refresh(); setInterval(refresh, 2500);
})();
