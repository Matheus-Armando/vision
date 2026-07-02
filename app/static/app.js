// DeZoio — helpers compartilhados: API, SSE, toasts, vídeo MJPEG e OSD.

async function api(method, url, body) {
  const opts = { method, headers: {} };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Erro ${res.status}`);
  }
  return res.json();
}

// ---------- toasts DeZoio (slideIn no canto) ----------
function toast(title, desc = '', type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'fixed bottom-6 right-6 z-50 space-y-2 max-w-sm w-full px-4 sm:px-0';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  const border = type === 'error' ? 'border-rose-900/70' : 'border-[#2d2d2d]';
  const dot = type === 'error' ? 'bg-rose-500' : 'bg-emerald-500';
  el.className = `bg-[#1c1c1c] border ${border} rounded-xl px-4 py-3 shadow-2xl animate-slideIn flex items-start gap-3`;
  el.innerHTML =
    `<span class="w-1.5 h-1.5 rounded-full ${dot} mt-1.5 shrink-0"></span>` +
    `<div><p class="text-xs font-bold text-white">${title}</p>` +
    (desc ? `<p class="text-[10px] text-[#888888] mt-0.5">${desc}</p>` : '') +
    `</div>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity 0.3s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 350);
  }, 3500);
}

// ---------- som de alerta ----------
let audioCtx;
function beep() {
  try {
    audioCtx = audioCtx || new AudioContext();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.frequency.value = 660;
    gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.5);
  } catch (e) { /* som é opcional */ }
}

// ---------- eventos ao vivo (SSE) ----------
// handlers.onEvents(list) e handlers.onBanner(bannerOuNull) são fornecidos pela página.
function startEventStream(handlers = {}) {
  let lastBannerText = null;
  const source = new EventSource('/events');
  source.onmessage = (msg) => {
    const snap = JSON.parse(msg.data);
    if (handlers.onBanner) handlers.onBanner(snap.banner);
    if (snap.banner && snap.banner.sound && snap.banner.text !== lastBannerText) beep();
    lastBannerText = snap.banner ? snap.banner.text : null;
    if (snap.events.length && handlers.onEvents) handlers.onEvents(snap.events);
  };
  return source;
}

// ---------- vídeo MJPEG ----------
// URL única por aba: sem isso o Chrome segura a 2ª requisição da mesma URL
// esperando a 1ª terminar (cache lock) — e um stream nunca termina.
// Também reconecta se o servidor reiniciar.
function freshVideoUrl() {
  return '/video_feed?t=' + Date.now() + Math.random().toString(36).slice(2);
}

function setupVideo() {
  for (const img of document.querySelectorAll('img[data-video]')) {
    img.src = freshVideoUrl();
    img.addEventListener('error', () => {
      if (img.dataset.off === '1') return;
      setTimeout(() => { img.src = freshVideoUrl(); }, 2000);
    });
  }
}
document.addEventListener('DOMContentLoaded', setupVideo);

// ---------- ícones ----------
function initLucide() {
  if (window.lucide) lucide.createIcons();
}

// ---------- relógio do OSD ----------
function startOsdClock(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const tick = () => { el.textContent = new Date().toLocaleTimeString('pt-BR'); };
  tick();
  setInterval(tick, 1000);
}

// ---------- sidebar das telas de gestão ----------
function renderSidebar(active) {
  const item = (href, icon, label, key) => `
    <a href="${href}" class="w-full text-left px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-3 transition-all ${key === active
      ? 'bg-[#222222] text-white border border-[#333333]'
      : 'text-[#888888] hover:text-white'}">
      <i data-lucide="${icon}" class="w-3.5 h-3.5"></i><span>${label}</span>
    </a>`;
  const el = document.getElementById('sidebar');
  el.className = 'w-full md:w-64 bg-[#181818] border-r border-[#262626] flex flex-col justify-between p-6 shrink-0 md:min-h-screen';
  el.innerHTML = `
    <div class="space-y-8">
      <a href="/"><img src="/static/brand/logo_svg_dezoio.svg" alt="DeZoio" class="h-8 w-auto object-contain"></a>
      <div class="space-y-1">
        <span class="text-[9px] font-bold text-[#888888] uppercase tracking-wider block">Ambiente</span>
        <h2 class="text-sm font-bold text-white truncate">${dzActiveWorkspace().name}</h2>
      </div>
      <nav class="space-y-1.5">
        ${item('/painel', 'layout-dashboard', 'Dashboard', 'dashboard')}
        ${item('/painel', 'sliders', 'Automação', 'automacao')}
      </nav>
      <div class="space-y-1.5 pt-4 border-t border-[#262626]">
        <span class="text-[9px] font-bold text-[#888888] uppercase tracking-wider block px-1 pb-1">Gestão</span>
        ${item('/pessoas', 'users', 'Pessoas', 'pessoas')}
        ${item('/objetos', 'box', 'Objetos', 'objetos')}
        ${item('/regras', 'git-branch', 'Regras', 'regras')}
      </div>
    </div>
    <div class="pt-6 border-t border-[#262626] mt-8">
      <a href="/" class="w-full flex items-center justify-center gap-2 text-xs font-bold text-[#888888] hover:text-white transition-all bg-[#222222]/35 hover:bg-[#222222] px-4 py-2.5 rounded-xl border border-[#2d2d2d]">
        <i data-lucide="log-out" class="w-3.5 h-3.5"></i><span>Trocar Ambiente</span>
      </a>
    </div>`;
  initLucide();
}

// ---------- ambientes (visuais, localStorage) ----------
const DZ_PRINCIPAL = { id: 'principal', name: 'Câmera Principal' };

function dzWorkspaces() {
  const extra = JSON.parse(localStorage.getItem('dz_workspaces') || '[]');
  return [DZ_PRINCIPAL, ...extra];
}

function dzActiveWorkspace() {
  const id = localStorage.getItem('dz_active_ws') || 'principal';
  return dzWorkspaces().find(w => w.id === id) || DZ_PRINCIPAL;
}
