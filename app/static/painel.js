// DeZoio Painel — dashboard real + wizard de automação (usa APIs existentes).

const ws = dzActiveWorkspace();
const isPrincipal = ws.id === 'principal';
let signalOn = true;

// ---------- log drawer ----------
let logDrawerOpen = false;
let logUnread = 0;
let logEventCount = 0;

function toggleLogDrawer() {
  logDrawerOpen = !logDrawerOpen;
  const drawer = document.getElementById('log-drawer');
  drawer.classList.toggle('translate-x-full', !logDrawerOpen);
  drawer.classList.toggle('translate-x-0', logDrawerOpen);
  if (logDrawerOpen) {
    logUnread = 0;
    updateLogBadge();
  }
  initLucide();
}

function clearLogDrawer() {
  logEventCount = 0;
  const tl = document.getElementById('events-timeline');
  tl.innerHTML = '<p class="text-xs text-[#888888] italic text-center py-4">Log limpo.</p>';
  document.getElementById('drawer-event-count').textContent = '0 eventos registrados';
}

function updateLogBadge() {
  const badge = document.getElementById('log-unread-badge');
  if (!badge) return;
  if (logUnread > 0) {
    badge.textContent = logUnread > 9 ? '9+' : logUnread;
    badge.classList.remove('hidden');
    badge.classList.add('flex');
  } else {
    badge.classList.add('hidden');
    badge.classList.remove('flex');
  }
}

// ---------- log queue (one-by-one, 10-item cap) ----------
const logQueue = [];
let logDraining = false;

function drainLogQueue() {
  if (logDraining || !logQueue.length) return;
  logDraining = true;
  const ev = logQueue.shift();
  appendLogEvent(ev);
  setTimeout(() => {
    logDraining = false;
    drainLogQueue();
  }, 350);
}

function appendLogEvent(ev) {
  const container = document.getElementById('events-timeline');
  if (container.querySelector('p')) container.innerHTML = '';

  const item = document.createElement('div');
  item.className = 'relative pl-4 border-l border-[#2d2d2d] pb-1 animate-fadeIn';
  const dot = ev.kind === 'rule' ? 'bg-neutral-100' : 'bg-[#555555]';
  const conf = ev.confidence ? ` · ${Math.round(ev.confidence * 100)}%` : '';
  item.innerHTML =
    `<span class="absolute -left-1 top-1.5 w-2 h-2 rounded-full ${dot}"></span>` +
    `<div class="flex justify-between items-baseline gap-2">` +
    `<h5 class="text-xs font-bold text-slate-200">${ev.message}</h5>` +
    `<span class="text-[9px] text-[#888888] shrink-0">${ev.time}</span></div>` +
    `<p class="text-[10px] text-[#888888] mt-0.5">${kindLabel(ev.kind)}${conf}${ev.rule ? ' · regra: ' + ev.rule : ''}</p>`;
  container.prepend(item);

  // keep max 10
  while (container.children.length > 10) container.removeChild(container.lastChild);

  logEventCount++;
  const fc = document.getElementById('drawer-event-count');
  if (fc) fc.textContent = `${logEventCount} evento${logEventCount !== 1 ? 's' : ''} registrado${logEventCount !== 1 ? 's' : ''}`;
  const ld = document.getElementById('drawer-live-dot');
  if (ld) ld.className = 'w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse';
  if (!logDrawerOpen) {
    logUnread++;
    updateLogBadge();
  }
}

// condições fiéis ao motor de regras (mesmos nomes do modelo) + visões futuras
const EVENT_OPTIONS = [
  { id: 'person_recognized', title: 'Pessoa reconhecida', desc: 'Dispara quando o perfil treinado (ou qualquer pessoa cadastrada) é reconhecido no visor.', real: true, needs: ['person'] },
  { id: 'unknown_person', title: 'Pessoa desconhecida detectada', desc: 'Dispara quando um rosto não cadastrado aparece na cena.', real: true, needs: [] },
  { id: 'object_detected', title: 'Objeto detectado', desc: 'Dispara quando o objeto escolhido aparece na cena.', real: true, needs: ['object'] },
  { id: 'person_with_object', title: 'Pessoa COM objeto', desc: 'Pessoa reconhecida portando o objeto (associação geométrica no enquadramento).', real: true, needs: ['person', 'object'] },
  { id: 'person_without_object', title: 'Pessoa SEM objeto', desc: 'Pessoa reconhecida sem o objeto — ex.: sem capacete/EPI.', real: true, needs: ['person', 'object'] },
  { id: 'object_absent', title: 'Objeto ausente da cena', desc: 'Dispara quando o objeto some do enquadramento por N segundos.', real: true, needs: ['object', 'seconds'] },
  { id: 'pessoa_entrou', title: 'Pessoa entrou', desc: 'Detecta a entrada cruzando barreiras virtuais.', real: false },
  { id: 'pessoa_saiu', title: 'Pessoa saiu', desc: 'Detecta a saída do perímetro delimitado.', real: false },
  { id: 'pessoa_permaneceu', title: 'Permaneceu por mais de X minutos', desc: 'Monitora permanência anormal.', real: false },
  { id: 'pessoa_nao_apareceu', title: 'Pessoa não apareceu hoje', desc: 'Notifica ausência ou descumprimento de turnos.', real: false },
  { id: 'pessoa_fora_horario', title: 'Apareceu fora de horário', desc: 'Alerta para acessos em horários de fechamento.', real: false },
];

const ACTION_OPTIONS = [
  { id: 'banner_green', title: 'Aviso no visor (liberado)', desc: 'Banner verde sobre o feed ao vivo.', real: true, radio: true },
  { id: 'banner_red', title: 'Alerta no visor', desc: 'Banner vermelho de alerta sobre o feed.', real: true, radio: true },
  { id: 'sound', title: 'Alerta sonoro', desc: 'Som de aviso no painel junto com o banner.', real: true, radio: false },
  { id: 'historico', title: 'Registrar histórico', desc: 'Evento gravado na linha do tempo (sempre ativo).', real: true, fixed: true },
  { id: 'whatsapp', title: 'Mensagem WhatsApp', desc: 'Envio de imagens em tempo real aos responsáveis.', real: false },
  { id: 'email', title: 'Email', desc: 'Disparo de resumos diários de conformidade.', real: false },
];

const TRIGGER_OPTIONS = [
  { id: 'once', title: '1x por aparição', desc: 'Dispara quando a condição passa a valer e re-arma quando ela deixa de valer.', real: true },
  { id: 'interval', title: 'A cada X segundos', desc: 'Repete no intervalo definido enquanto a condição valer.', real: true },
];

const CONDITION_LABELS = {
  person_recognized: 'Pessoa reconhecida',
  unknown_person: 'Pessoa desconhecida detectada',
  object_detected: 'Objeto detectado',
  person_with_object: 'Pessoa COM objeto',
  person_without_object: 'Pessoa SEM objeto',
  object_absent: 'Objeto ausente da cena',
};

// ---------------- estado do wizard ----------------
const wz = {};
resetWizardState();

function resetWizardState() {
  return Object.assign(wz, {
    step: 1,
    personId: null,
    personName: '',
    photosTrained: 0,
    event: 'person_recognized',
    eventObject: null,
    actionType: 'banner_green',
    sound: false,
    actionText: '',
    triggerMode: 'once',
    triggerSeconds: 10,
    objects: [],
    captures: [],
  });
}

// ---------------- inicialização ----------------
document.getElementById('sidebar-ws-name').textContent = ws.name;
document.getElementById('feed-channel').textContent = `| ${ws.name}`;

if (!isPrincipal) {
  signalOn = false;
  const img = document.getElementById('video-img');
  img.dataset.off = '1';
  img.removeAttribute('src');
  showCameraOff('Sem câmera vinculada',
    'Este ambiente está em standby. Vincular novas câmeras chega em breve — use o ambiente Câmera Principal.');
  document.getElementById('btn-toggle-signal').classList.add('hidden');
}

switchMenu('dashboard');
startOsdClock('osd-clock');
initLucide();
pollStatus();
pollStats();
loadNodes();

startEventStream({
  onBanner(banner) {
    const el = document.getElementById('rule-banner');
    const base = 'absolute top-14 left-1/2 -translate-x-1/2 z-20 px-7 py-2.5 rounded-xl text-sm font-extrabold tracking-wide shadow-2xl transition-opacity duration-300 whitespace-nowrap';
    if (banner) {
      el.textContent = banner.text;
      el.className = base + (banner.color === 'green'
        ? ' bg-emerald-400 text-emerald-950'
        : ' bg-rose-600 text-white') + ' opacity-100';
    } else {
      el.className = base + ' opacity-0';
    }
  },
  onEvents(events) {
    for (const ev of events) logQueue.push(ev);
    drainLogQueue();
  },
});

function kindLabel(kind) {
  return { face: 'Reconhecimento facial', object: 'Detecção de objeto', rule: 'Automação', system: 'Sistema' }[kind] || kind;
}

// ---------------- menus ----------------
function switchMenu(menu) {
  document.getElementById('pane-dashboard').classList.toggle('hidden', menu !== 'dashboard');
  document.getElementById('pane-automacao').classList.toggle('hidden', menu !== 'automacao');
  const active = 'bg-[#222222] text-white border border-[#333333]';
  const idle = 'text-[#888888] hover:text-white border border-transparent';
  document.getElementById('btn-menu-dashboard').className =
    `w-full text-left px-4 py-3 rounded-xl text-xs font-semibold flex items-center gap-3 transition-all ${menu === 'dashboard' ? active : idle}`;
  document.getElementById('btn-menu-automacao').className =
    `w-full text-left px-4 py-3 rounded-xl text-xs font-semibold flex items-center gap-3 transition-all ${menu === 'automacao' ? active : idle}`;
  if (menu === 'dashboard') loadNodes();
}

// ---------------- player ----------------
function toggleSignal() {
  const img = document.getElementById('video-img');
  const label = document.getElementById('btn-toggle-signal-text');
  signalOn = !signalOn;
  if (signalOn) {
    img.dataset.off = '0';
    img.src = freshVideoUrl();
    document.getElementById('camera-off').classList.add('hidden');
    label.textContent = 'Desligar Sinal';
  } else {
    img.dataset.off = '1';
    img.removeAttribute('src');
    showCameraOff('Sem sinal de vídeo', 'Sinal suspenso pelo operador. Ative o feed para retomar a varredura.');
    label.textContent = 'Ligar Sinal';
  }
}

function showCameraOff(title, desc) {
  document.getElementById('camera-off-title').textContent = title;
  document.getElementById('camera-off-desc').textContent = desc;
  document.getElementById('camera-off').classList.remove('hidden');
  initLucide();
}

async function pollStatus() {
  try {
    const st = await api('GET', '/api/status');
    const online = st.camera === 'ao vivo';
    document.getElementById('osd-res').textContent = `RES: 1280x720 @ ${st.fps || '—'} FPS`;
    document.getElementById('badge-status-dot').className =
      `w-1.5 h-1.5 rounded-full ${online ? 'bg-emerald-500 animate-pulse' : 'bg-rose-600'}`;
    document.getElementById('badge-status-text').textContent =
      online ? 'Monitoramento Ativo' : 'Câmera indisponível';
  } catch (e) { /* servidor subindo */ }
  setTimeout(pollStatus, 2500);
}

async function pollStats() {
  try {
    const s = await api('GET', '/api/stats');
    document.getElementById('stat-identificacoes').textContent = s.identificacoes;
    document.getElementById('stat-eventos').textContent = s.eventos;
    document.getElementById('stat-regras').textContent = s.regras;
    document.getElementById('stat-precisao').textContent = s.precisao ? `${s.precisao}%` : '—';
  } catch (e) { /* ignore */ }
  setTimeout(pollStats, 3000);
}

async function loadNodes() {
  try {
    const [rules, meta] = await Promise.all([api('GET', '/api/rules'), api('GET', '/api/rules/meta')]);
    const container = document.getElementById('nodes-list');
    if (!rules.length) {
      container.innerHTML = '<p class="text-xs text-[#888888] italic text-center py-4">Nenhum nó de reconhecimento configurado.</p>';
      return;
    }
    container.innerHTML = rules.map(rule => {
      const cond = describeCondition(rule.condition, meta);
      return `
        <div class="bg-[#121212] border border-[#222222] p-4 rounded-xl flex justify-between items-center gap-3">
          <div class="min-w-0">
            <h5 class="text-xs font-bold text-white truncate">${rule.name}</h5>
            <p class="text-[10px] text-[#888888] mt-0.5 truncate">Rastreando: ${cond}</p>
          </div>
          <span class="text-[10px] shrink-0 ${rule.enabled
            ? 'text-white bg-[#222222] border border-[#333333]'
            : 'text-[#888888] bg-transparent border border-[#2d2d2d]'} px-2.5 py-0.5 rounded-full font-bold">
            ${rule.enabled ? 'Ativo' : 'Pausado'}
          </span>
        </div>`;
    }).join('');
  } catch (e) { /* ignore */ }
}

function describeCondition(cond, meta) {
  let desc = CONDITION_LABELS[cond.type] || cond.type;
  if (cond.person_id && meta) {
    const p = meta.people.find(p => p.id === cond.person_id);
    if (p) desc += ` — ${p.name}`;
  }
  if (cond.object && meta) {
    const o = meta.objects.find(o => o.cls === cond.object);
    desc += ` — ${o ? o.label : cond.object}`;
  }
  return desc;
}

// ---------------- wizard ----------------
async function startWizard() {
  resetWizardState();
  document.getElementById('automacao-categorias').classList.add('hidden');
  document.getElementById('automacao-wizard').classList.remove('hidden');
  document.getElementById('wz-name').value = '';
  document.getElementById('wz-files').value = '';
  document.getElementById('wz-file-list').innerHTML = '';
  document.getElementById('wz-capture-list').innerHTML = '';
  document.getElementById('wz-train-progress').classList.add('hidden');
  document.getElementById('wz-train-done').classList.add('hidden');
  document.getElementById('wz-btn-train').classList.remove('hidden');
  document.getElementById('wz-action-text').value = '';
  try {
    const meta = await api('GET', '/api/rules/meta');
    const seen = new Set();
    wz.objects = meta.objects
      .filter(o => !seen.has(o.label) && seen.add(o.label))
      .sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'));
  } catch (e) { wz.objects = []; }
  renderWizard();
}

function cancelWizard() {
  document.getElementById('automacao-wizard').classList.add('hidden');
  document.getElementById('automacao-categorias').classList.remove('hidden');
}

function renderWizard() {
  document.querySelectorAll('.wizard-step').forEach((el, i) => {
    el.classList.toggle('hidden', i + 1 !== wz.step);
  });
  document.querySelectorAll('.wizard-tab').forEach(tab => {
    const active = Number(tab.dataset.step) === wz.step;
    tab.className = `wizard-tab px-3 py-1.5 rounded-full transition-all border whitespace-nowrap ${active
      ? 'bg-white text-black border-white'
      : 'bg-[#1c1c1c] text-[#888888] border-[#2d2d2d] hover:text-white'}`;
    tab.onclick = () => { if (Number(tab.dataset.step) < wz.step) { wz.step = Number(tab.dataset.step); renderWizard(); } };
  });
  document.getElementById('wz-btn-next').textContent = wz.step === 5 ? 'Ativar Automação' : 'Avançar';
  if (wz.step === 2) renderEventCards();
  if (wz.step === 3) renderActionCards();
  if (wz.step === 4) renderTriggerCards();
  if (wz.step === 5) renderSummary();
  initLucide();
}

function selectionCard({ title, desc, selected, disabled, onclick, shape }) {
  const border = disabled ? 'border-[#222222] bg-[#121212]/50 opacity-40 select-none'
    : selected ? 'border-white bg-[#1c1c1c] cursor-pointer'
    : 'border-[#262626] bg-[#1c1c1c]/40 hover:border-neutral-500 cursor-pointer';
  const indicator = disabled
    ? '<span class="bg-[#222222] text-[#888888] text-[8px] font-bold px-2 py-0.5 rounded-full shrink-0">Em breve</span>'
    : `<div class="w-3.5 h-3.5 ${shape === 'square' ? 'rounded' : 'rounded-full'} border ${selected
        ? 'border-white bg-white flex items-center justify-center'
        : 'border-[#333333]'} shrink-0">${selected ? '<i data-lucide="check" class="w-2.5 h-2.5 text-black"></i>' : ''}</div>`;
  return `
    <div ${onclick && !disabled ? `onclick="${onclick}"` : ''} class="p-4 rounded-xl border ${border} transition-all flex items-start gap-3 justify-between">
      <div>
        <h4 class="font-semibold text-xs ${disabled ? 'text-slate-400' : 'text-white'}">${title}</h4>
        <p class="text-[10px] ${disabled ? 'text-[#555555]' : 'text-[#888888]'} mt-1">${desc}</p>
      </div>
      ${indicator}
    </div>`;
}

// etapa 1 — treino real
function wizardFilesChanged() {
  const files = document.getElementById('wz-files').files;
  const list = document.getElementById('wz-file-list');
  list.innerHTML = [...files].map(f =>
    `<span class="bg-[#1c1c1c] border border-[#2d2d2d] text-[10px] text-slate-300 px-2.5 py-1 rounded-full">${f.name}</span>`
  ).join('');
}

async function wizardCapture() {
  try {
    // frame cru do servidor (sem as caixas desenhadas) — melhor para o treino
    const res = await fetch('/api/snapshot?t=' + Date.now());
    if (!res.ok) throw new Error('Câmera ainda não está ao vivo');
    const blob = await res.blob();
    wz.captures.push(new File([blob], `captura_${wz.captures.length + 1}.jpg`, { type: 'image/jpeg' }));
    renderCaptureChips();
    toast('Foto capturada', `${wz.captures.length} captura(s) na fila de treino.`);
  } catch (e) {
    toast('Erro na captura', e.message, 'error');
  }
}

function renderCaptureChips() {
  document.getElementById('wz-capture-list').innerHTML = wz.captures.map((f, i) =>
    `<span class="inline-flex items-center gap-1.5 bg-[#121212] border border-[#2d2d2d] text-[10px] text-slate-300 pl-2.5 pr-1 py-1 rounded-full">
       ${f.name}
       <button onclick="removeCapture(${i})" class="text-[#666666] hover:text-rose-400 px-1 leading-none">×</button>
     </span>`).join('');
}

function removeCapture(i) {
  wz.captures.splice(i, 1);
  renderCaptureChips();
}

async function runTraining() {
  const name = document.getElementById('wz-name').value.trim();
  const files = [...document.getElementById('wz-files').files, ...wz.captures];
  if (!name) return toast('Falta o nome', 'Dê um identificador ao perfil.', 'error');
  if (!files.length) return toast('Faltam as fotos', 'Envie imagens ou capture pela câmera.', 'error');

  const btn = document.getElementById('wz-btn-train');
  const progress = document.getElementById('wz-train-progress');
  const bar = document.getElementById('wz-train-bar');
  const percent = document.getElementById('wz-train-percent');
  btn.classList.add('hidden');
  progress.classList.remove('hidden');

  try {
    const person = await api('POST', '/api/people', { name });
    wz.personId = person.id;
    wz.personName = name;
    let processed = 0, skipped = 0;
    for (let i = 0; i < files.length; i++) {
      const form = new FormData();
      form.append('files', files[i]);
      const res = await api('POST', `/api/people/${person.id}/photos`, form);
      processed += res.processed;
      skipped += res.skipped;
      const pct = Math.round(((i + 1) / files.length) * 100);
      bar.style.width = pct + '%';
      percent.textContent = pct + '%';
    }
    wz.photosTrained = processed;
    progress.classList.add('hidden');
    if (!processed) {
      btn.classList.remove('hidden');
      return toast('Nenhum rosto encontrado', 'Tente fotos mais nítidas e de frente.', 'error');
    }
    document.getElementById('wz-train-done-text').textContent =
      `Modelo calibrado: ${processed} rosto(s)` + (skipped ? ` (${skipped} foto(s) sem rosto)` : '');
    document.getElementById('wz-train-done').classList.remove('hidden');
    initLucide();
    toast('Perfil treinado', `${name} já é reconhecido pela câmera.`);
  } catch (e) {
    btn.classList.remove('hidden');
    progress.classList.add('hidden');
    toast('Erro no treinamento', e.message, 'error');
  }
}

// etapa 2 — evento
function eventNeeds() {
  return (EVENT_OPTIONS.find(o => o.id === wz.event) || {}).needs || [];
}

function renderEventCards() {
  document.getElementById('wz-events').innerHTML = EVENT_OPTIONS.map(opt =>
    selectionCard({
      title: opt.title, desc: opt.desc,
      selected: wz.event === opt.id,
      disabled: !opt.real,
      onclick: `selectWzEvent('${opt.id}')`,
    })).join('');
  const needs = eventNeeds();
  const objWrap = document.getElementById('wz-event-object-wrap');
  objWrap.classList.toggle('hidden', !needs.includes('object'));
  if (needs.includes('object')) {
    const sel = document.getElementById('wz-event-object');
    sel.innerHTML = wz.objects.map(o => `<option value="${o.cls}">${o.label}</option>`).join('');
    if (wz.eventObject) sel.value = wz.eventObject;
  }
  document.getElementById('wz-event-seconds-wrap')
    .classList.toggle('hidden', !needs.includes('seconds'));
  initLucide();
}

function selectWzEvent(id) {
  wz.event = id;
  renderEventCards();
}

// etapa 3 — resposta
function renderActionCards() {
  document.getElementById('wz-actions').innerHTML = ACTION_OPTIONS.map(opt => {
    const selected = opt.fixed ? true
      : opt.radio ? wz.actionType === opt.id
      : opt.id === 'sound' ? wz.sound : false;
    return selectionCard({
      title: opt.title, desc: opt.desc,
      selected,
      disabled: !opt.real,
      onclick: opt.fixed ? '' : `selectWzAction('${opt.id}')`,
      shape: opt.radio ? 'circle' : 'square',
    });
  }).join('');
  const text = document.getElementById('wz-action-text');
  if (!text.value) {
    text.value = wz.actionType === 'banner_green' ? 'ACESSO LIBERADO — {nome}' : 'ALERTA — {nome}';
  }
  initLucide();
}

function selectWzAction(id) {
  if (id === 'sound') {
    wz.sound = !wz.sound;
  } else {
    const previous = wz.actionType;
    wz.actionType = id;
    const text = document.getElementById('wz-action-text');
    const defaults = { banner_green: 'ACESSO LIBERADO — {nome}', banner_red: 'ALERTA — {nome}' };
    if (!text.value || text.value === defaults[previous]) text.value = defaults[id];
  }
  renderActionCards();
}

// etapa 4 — disparo
function renderTriggerCards() {
  document.getElementById('wz-triggers').innerHTML = TRIGGER_OPTIONS.map(opt =>
    selectionCard({
      title: opt.title, desc: opt.desc,
      selected: wz.triggerMode === opt.id,
      disabled: !opt.real,
      onclick: `selectWzTrigger('${opt.id}')`,
    })).join('');
  document.getElementById('wz-trigger-seconds-wrap').classList.toggle('hidden', wz.triggerMode !== 'interval');
  initLucide();
}

function selectWzTrigger(id) {
  wz.triggerMode = id;
  renderTriggerCards();
}

// etapa 5 — resumo
function renderSummary() {
  const eventOpt = EVENT_OPTIONS.find(o => o.id === wz.event);
  const needs = eventNeeds();
  const objLabel = wz.objects.find(o => o.cls === document.getElementById('wz-event-object').value)?.label;
  document.getElementById('wz-sum-ws').textContent = ws.name;
  document.getElementById('wz-sum-profile').textContent =
    wz.personName || (needs.includes('person') ? 'Qualquer pessoa cadastrada' : '—');
  document.getElementById('wz-sum-photos').textContent = wz.photosTrained ? `${wz.photosTrained} imagem(ns) calibradas` : '';
  let eventText = eventOpt.title;
  if (needs.includes('object') && objLabel) eventText += ` — ${objLabel}`;
  if (needs.includes('seconds')) {
    eventText += ` — ${Number(document.getElementById('wz-event-seconds').value) || 5}s`;
  }
  document.getElementById('wz-sum-event').textContent = eventText;
  const badges = [
    wz.actionType === 'banner_green' ? 'Aviso verde no visor' : 'Alerta vermelho no visor',
    wz.sound ? 'Som de alerta' : null,
    'Histórico',
  ].filter(Boolean);
  document.getElementById('wz-sum-actions').innerHTML = badges.map(b =>
    `<span class="bg-[#282828] border border-[#383838] text-white text-[9px] font-bold px-2.5 py-1 rounded-full">${b}</span>`
  ).join('');
  document.getElementById('wz-sum-trigger').textContent =
    wz.triggerMode === 'once' ? '1x por aparição'
      : `A cada ${document.getElementById('wz-trigger-seconds').value || 10} segundos`;
}

// navegação
function wizardPrev() {
  if (wz.step > 1) { wz.step--; renderWizard(); }
  else cancelWizard();
}

async function wizardNext() {
  if (wz.step === 2 && eventNeeds().includes('object')) {
    wz.eventObject = document.getElementById('wz-event-object').value;
    if (!wz.eventObject) return toast('Escolha o objeto', '', 'error');
  }
  if (wz.step < 5) {
    wz.step++;
    renderWizard();
    return;
  }
  await activateAutomation();
}

async function activateAutomation() {
  const needs = eventNeeds();
  const condition = { type: wz.event };
  // sem perfil treinado, condições de pessoa valem para "qualquer pessoa"
  if (needs.includes('person')) condition.person_id = wz.personId || null;
  if (needs.includes('object')) condition.object = document.getElementById('wz-event-object').value;
  if (needs.includes('seconds')) {
    condition.seconds = Number(document.getElementById('wz-event-seconds').value) || 5;
  }
  const rule = {
    name: wz.personName ? `Monitor — ${wz.personName}` : `Monitor — ${EVENT_OPTIONS.find(o => o.id === wz.event).title}`,
    condition,
    action: {
      type: wz.actionType,
      text: document.getElementById('wz-action-text').value,
      sound: wz.sound,
    },
    trigger: {
      mode: wz.triggerMode,
      seconds: Number(document.getElementById('wz-trigger-seconds').value) || 10,
    },
  };
  try {
    await api('POST', '/api/rules', rule);
    toast('Automação ativada', 'A regra já está valendo na câmera.');
    cancelWizard();
    switchMenu('dashboard');
  } catch (e) {
    toast('Erro ao ativar', e.message, 'error');
  }
}
