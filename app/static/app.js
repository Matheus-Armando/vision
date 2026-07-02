// Helpers compartilhados: API, SSE de eventos, banner, toast e status.

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

function toast(message, isError = false) {
  const el = document.getElementById('toast');
  if (!el) return alert(message);
  el.textContent = message;
  el.style.borderLeftColor = isError ? 'var(--red)' : 'var(--accent)';
  el.classList.add('show');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 3000);
}

// ---------- eventos ao vivo (SSE) ----------
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

function startEventStream() {
  const list = document.getElementById('event-list');
  const banner = document.getElementById('banner');
  let lastBannerText = null;

  const source = new EventSource('/events');
  source.onmessage = (msg) => {
    const snap = JSON.parse(msg.data);

    if (banner) {
      if (snap.banner) {
        banner.textContent = snap.banner.text;
        banner.className = `banner show ${snap.banner.color}`;
        if (snap.banner.sound && snap.banner.text !== lastBannerText) beep();
        lastBannerText = snap.banner.text;
      } else {
        banner.classList.remove('show');
        lastBannerText = null;
      }
    }

    if (list && snap.events.length) {
      for (const ev of snap.events) {
        const el = document.createElement('div');
        el.className = 'event';
        const conf = ev.confidence ? `<span class="conf">${Math.round(ev.confidence * 100)}%</span>` : '';
        const kindLabel = { face: 'rosto', object: 'objeto', rule: 'regra', system: 'sistema' }[ev.kind] || ev.kind;
        el.innerHTML = `<span class="badge ${ev.kind}">${kindLabel}</span>` +
          `<span class="msg">${ev.message}</span>${conf}<span class="time">${ev.time}</span>`;
        list.prepend(el);
      }
      while (list.children.length > 60) list.removeChild(list.lastChild);
    }
  };
}

// ---------- vídeo MJPEG ----------
// URL única por aba: sem isso o Chrome segura a 2ª requisição da mesma URL
// esperando a 1ª terminar (cache lock) — e um stream nunca termina.
// Também reconecta se o servidor reiniciar.
function setupVideo() {
  for (const img of document.querySelectorAll('img[src^="/video_feed"]')) {
    img.src = '/video_feed?t=' + Date.now() + Math.random().toString(36).slice(2);
    img.addEventListener('error', () => {
      setTimeout(() => {
        img.src = '/video_feed?t=' + Date.now() + Math.random().toString(36).slice(2);
      }, 2000);
    });
  }
}
document.addEventListener('DOMContentLoaded', setupVideo);

// ---------- status ----------
async function pollStatus() {
  const setDot = (id, on) => {
    const el = document.getElementById(id);
    if (el) el.className = `dot ${on ? 'on' : 'off'}`;
  };
  try {
    const st = await api('GET', '/api/status');
    setDot('dot-faces', st.faces_ready);
    setDot('dot-objects', st.objects_ready);
    setDot('dot-camera', st.camera === 'ao vivo');
    const cam = document.getElementById('st-camera');
    if (cam) cam.textContent = st.camera;
    const fps = document.getElementById('st-fps');
    if (fps) fps.textContent = st.fps || '—';
  } catch (e) { /* servidor subindo */ }
  setTimeout(pollStatus, 2000);
}
