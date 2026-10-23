const input = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-btn');
const messages = document.querySelector('#messages');
const count = document.querySelector('#char-count');
const statusDot = document.querySelector('#status-dot');
const statusText = document.querySelector('#status-text');
const mapTitle = document.querySelector('#map-title');
const mapStatus = document.querySelector('#map-status');
const mapStops = document.querySelector('#map-stops');
const workspace = document.querySelector('.workspace');
const mapPanel = document.querySelector('.map-panel');
const threadKey = 'xingji-thread-id';
let threadId = sessionStorage.getItem(threadKey) || `web-${crypto.randomUUID()}`;
let map;
let routeLayer;
let selectionId = 0;
let lastGeocodeAt = 0;
let geocodeQueue = Promise.resolve();
const geocodeCache = new Map();
sessionStorage.setItem(threadKey, threadId);

function addMessage(text, role) {
  document.querySelector('.welcome')?.remove();
  const item = document.createElement('div');
  item.className = `message ${role}`;
  const body = document.createElement('div');
  body.className = 'message-body';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  const label = document.createElement('span');
  label.className = 'role';
  label.textContent = role === 'user' ? '你' : '行迹';
  body.appendChild(bubble);
  item.append(body, label);
  messages.appendChild(item);
  messages.scrollTop = messages.scrollHeight;
  return body;
}

function renderRoutes(container, routes) {
  if (!Array.isArray(routes) || routes.length === 0) return;
  const list = document.createElement('div');
  list.className = 'route-list';
  const heading = document.createElement('div');
  heading.className = 'route-list-heading';
  heading.textContent = '可选路线';
  list.appendChild(heading);
  routes.forEach((route, index) => {
    if (!Array.isArray(route.stops) || route.stops.length < 2) return;
    const card = document.createElement('article');
    card.className = 'route-card';
    const top = document.createElement('div');
    top.className = 'route-card-top';
    const number = document.createElement('span');
    number.className = 'route-number';
    number.textContent = String(index + 1).padStart(2, '0');
    const title = document.createElement('h3');
    title.textContent = route.title;
    top.append(number, title);
    const description = document.createElement('p');
    description.textContent = route.description;
    const stops = document.createElement('div');
    stops.className = 'route-stop-preview';
    stops.textContent = route.stops.map(stop => stop.name).join('  →  ');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'route-select';
    button.textContent = '选择并查看地图';
    button.addEventListener('click', () => {
      document.querySelectorAll('.route-card.selected').forEach(item => item.classList.remove('selected'));
      document.querySelectorAll('.route-select').forEach(item => { item.textContent = '选择并查看地图'; item.setAttribute('aria-pressed', 'false'); });
      card.classList.add('selected');
      button.textContent = '已选择 · 查看地图';
      button.setAttribute('aria-pressed', 'true');
      selectRoute(route);
    });
    card.append(top, description, stops, button);
    list.appendChild(card);
  });
  container.appendChild(list);
}

function ensureMap() {
  if (!window.L) throw new Error('地图组件未加载，请检查网络连接');
  if (!map) {
    map = L.map('map', { zoomControl: true }).setView([31.2304, 121.4737], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
    }).addTo(map);
  }
  document.querySelector('#map-empty').hidden = true;
  requestAnimationFrame(() => map.invalidateSize());
}

async function revealMapPanel() {
  if (workspace.classList.contains('map-open')) return;
  mapPanel.inert = false;
  mapPanel.setAttribute('aria-hidden', 'false');
  workspace.classList.add('map-open');
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    await new Promise(resolve => setTimeout(resolve, 560));
  }
}

function closeMapPanel() {
  selectionId++;
  workspace.classList.remove('map-open');
  mapPanel.inert = true;
  mapPanel.setAttribute('aria-hidden', 'true');
}

async function geocode(name, destination) {
  const query = `${name}, ${destination}`;
  if (geocodeCache.has(query)) return geocodeCache.get(query);
  geocodeQueue = geocodeQueue.catch(() => {}).then(async () => {
    if (geocodeCache.has(query)) return geocodeCache.get(query);
    const wait = Math.max(0, 1100 - (Date.now() - lastGeocodeAt));
    if (wait) await new Promise(resolve => setTimeout(resolve, wait));
    lastGeocodeAt = Date.now();
    const url = `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=${encodeURIComponent(query)}`;
    const response = await fetch(url, { headers: { 'Accept-Language': 'zh-CN,zh;q=0.9' } });
    if (!response.ok) throw new Error('地点定位服务暂时不可用');
    const matches = await response.json();
    const result = matches.length ? [Number(matches[0].lat), Number(matches[0].lon)] : null;
    geocodeCache.set(query, result);
    return result;
  });
  return geocodeQueue;
}

async function selectRoute(route) {
  const currentSelection = ++selectionId;
  mapTitle.textContent = route.title;
  mapStops.replaceChildren();
  mapStatus.textContent = '正在定位路线中的地点…';
  try {
    await revealMapPanel();
    if (currentSelection !== selectionId) return;
    mapPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    ensureMap();
    if (routeLayer) routeLayer.remove();
    routeLayer = L.layerGroup().addTo(map);
    const points = [];
    const missing = [];
    for (const [index, stop] of route.stops.entries()) {
      if (currentSelection !== selectionId) return;
      let coordinates;
      try { coordinates = await geocode(stop.name, route.destination); }
      catch (error) {
        if (currentSelection !== selectionId) return;
        mapStatus.textContent = `${error.message}。已显示定位成功的站点。`;
        break;
      }
      if (currentSelection !== selectionId) return;
      if (!coordinates) { missing.push(stop.name); continue; }
      const [lat, lon] = coordinates;
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) { missing.push(stop.name); continue; }
      points.push(coordinates);
      const icon = L.divIcon({ className: 'map-pin', html: `<span>${index + 1}</span>`, iconSize: [28, 28], iconAnchor: [14, 14] });
      L.marker(coordinates, { icon }).bindPopup(`<strong>${escapeHtml(stop.name)}</strong><br>${escapeHtml(stop.description || '')}`).addTo(routeLayer);
      const row = document.createElement('div');
      row.className = 'map-stop';
      const badge = document.createElement('span'); badge.textContent = String(index + 1);
      const info = document.createElement('div');
      const name = document.createElement('strong'); name.textContent = stop.name;
      const detail = document.createElement('small'); detail.textContent = stop.description || '';
      info.append(name, detail); row.append(badge, info); mapStops.appendChild(row);
      mapStatus.textContent = `已定位 ${points.length} / ${route.stops.length} 个地点…`;
    }
    if (currentSelection !== selectionId) return;
    if (points.length > 1) L.polyline(points, { color: '#de6b47', weight: 4, opacity: 0.85, dashArray: '7 7' }).addTo(routeLayer);
    if (points.length) map.fitBounds(L.latLngBounds(points).pad(0.2), { maxZoom: 14 });
    mapStatus.textContent = points.length
      ? `已标记 ${points.length} 个地点${missing.length ? `；未找到：${missing.join('、')}` : ''}。虚线仅表示访问顺序。`
      : '没有找到可标记的地点，请尝试另一条路线。';
  } catch (error) {
    if (currentSelection === selectionId) mapStatus.textContent = error.message;
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text || sendButton.disabled) return;
  const requestThreadId = threadId;
  addMessage(text, 'user');
  input.value = '';
  input.dispatchEvent(new Event('input'));
  sendButton.disabled = true;
  const typing = document.createElement('div');
  typing.className = 'typing';
  typing.textContent = '行迹正在整理你的想法…';
  messages.appendChild(typing);
  messages.scrollTop = messages.scrollHeight;
  try {
    const response = await fetch('/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, thread_id: requestThreadId })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '服务暂时不可用');
    typing.remove();
    if (requestThreadId !== threadId) return;
    renderRoutes(addMessage(data.answer, 'assistant'), data.routes);
    messages.scrollTop = messages.scrollHeight;
  } catch (error) {
    typing.remove();
    if (requestThreadId !== threadId) return;
    addMessage(`暂时无法完成规划：${error.message}。请稍后重试。`, 'assistant');
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
}

input.addEventListener('input', () => {
  count.textContent = `${input.value.length} / 4000`;
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 130)}px`;
});
input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage(); }
});
sendButton.addEventListener('click', sendMessage);
document.querySelectorAll('.suggestion').forEach(button => button.addEventListener('click', () => {
  input.value = button.dataset.prompt;
  input.dispatchEvent(new Event('input'));
  input.focus();
}));
document.querySelector('#clear-btn').addEventListener('click', () => {
  closeMapPanel();
  sessionStorage.removeItem(threadKey);
  threadId = `web-${crypto.randomUUID()}`;
  sessionStorage.setItem(threadKey, threadId);
  messages.innerHTML = '<div class="welcome"><span class="welcome-icon">✦</span><h3>新的旅程，从这里开始。</h3><p>告诉我目的地、时间和偏好，我们一起把路线变得具体。</p></div>';
  mapTitle.textContent = '路线地图';
  mapStatus.textContent = '选择路线后显示地点和示意连线。';
  mapStops.replaceChildren();
  if (routeLayer) routeLayer.remove();
  document.querySelector('#map-empty').hidden = false;
});
document.querySelector('#close-map-btn').addEventListener('click', closeMapPanel);

fetch('/health').then(response => {
  if (!response.ok) throw new Error();
  statusDot.classList.add('online');
  statusText.textContent = '服务已连接';
}).catch(() => { statusText.textContent = '服务未连接'; });
