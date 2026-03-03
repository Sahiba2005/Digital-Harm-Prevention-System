
// ─────────────────────────────────────────────
//  BEHAVIOR TRACKING
// ─────────────────────────────────────────────
const behavior = {
  clicks: [],
  rapidClicks: 0,
  attempts: {},
  lastInterval: 0,

  recordClick() {
    const now = Date.now();
    if (this.clicks.length > 0) {
      this.lastInterval = now - this.clicks[this.clicks.length - 1];
    }
    this.clicks.push(now);
    // Keep only last 10 clicks in a 5s window
    this.clicks = this.clicks.filter(t => now - t < 5000);
    this.rapidClicks = this.clicks.length;
    this.updateUI();
  },

  recordAttempt(action) {
    this.attempts[action] = (this.attempts[action] || 0) + 1;
    this.updateUI();
  },

  get totalAttempts() {
    return Object.values(this.attempts).reduce((a,b) => a+b, 0);
  },

  get isPanic() {
    return this.rapidClicks >= 5 || this.totalAttempts >= 4 ||
      (this.lastInterval > 0 && this.lastInterval < 300);
  },

  get speedClass() {
    if (this.isPanic) return 'Panic';
    if (this.rapidClicks >= 3 || (this.lastInterval > 0 && this.lastInterval < 700)) return 'Rushed';
    return 'Normal';
  },

  get behaviorScore() {
    let s = 0;
    s += Math.min(this.rapidClicks * 4, 20);
    s += Math.min(this.totalAttempts * 5, 20);
    if (this.lastInterval > 0 && this.lastInterval < 400) s += 15;
    return s;
  },

  get mlClass() {
    const sc = this.speedClass;
    if (sc === 'Panic') return 'Panic-like';
    if (sc === 'Rushed') return 'Rushed';
    return 'Normal';
  },

  updateUI() {
    document.getElementById('b-clicks').textContent = this.rapidClicks;
    document.getElementById('b-attempts').textContent = this.totalAttempts;
    document.getElementById('b-interval').textContent =
      this.lastInterval > 0 ? this.lastInterval : '—';
    document.getElementById('b-speed').textContent = this.speedClass;

    const ind = document.getElementById('panic-ind');
    const ml = document.getElementById('ml-class');
    if (this.isPanic) {
      ind.className = 'panic-indicator panic';
      ind.innerHTML = '<span>⚠</span> Panic-like behavior detected!';
    } else {
      ind.className = 'panic-indicator';
      ind.innerHTML = '<span>✓</span> Normal behavior detected';
    }
    ml.textContent = this.mlClass;
  }
};

// Track all clicks on the page
document.addEventListener('click', e => {
  if (!e.target.closest('header')) behavior.recordClick();
});

// ─────────────────────────────────────────────
//  RISK ENGINE
// ─────────────────────────────────────────────
const ACTION_BASE_SCORES = { send: 30, delete: 25, share: 20 };

const AMOUNT_THRESHOLDS = [
  { limit: 1000, score: 0 },
  { limit: 10000, score: 10 },
  { limit: 50000, score: 20 },
  { limit: Infinity, score: 35 }
];

const FILE_TYPE_SCORES = { document: 10, backup: 20, system: 30, media: 5 };

const DATA_SENSITIVITY = {
  personal: 15, financial: 25, credentials: 35, medical: 20
};

function calcRisk(action, params) {
  let actionScore = ACTION_BASE_SCORES[action] || 20;
  let amountScore = 0;

  if (action === 'send') {
    const amt = parseFloat(params.amount) || 0;
    for (const t of AMOUNT_THRESHOLDS) {
      if (amt <= t.limit) { amountScore = t.score; break; }
    }
  } else if (action === 'delete') {
    amountScore = FILE_TYPE_SCORES[params.fileType] || 10;
  } else if (action === 'share') {
    amountScore = DATA_SENSITIVITY[params.dataType] || 15;
  }

  const behaviorScore = behavior.behaviorScore;
  const panicPenalty = behavior.isPanic ? 20 : 0;

  const total = Math.min(actionScore + amountScore + behaviorScore + panicPenalty, 100);
  const level = total >= 70 ? 'high' : total >= 40 ? 'medium' : 'low';

  return { total, level, actionScore, amountScore, behaviorScore, panicPenalty };
}

// ─────────────────────────────────────────────
//  FORM OPEN / CLOSE
// ─────────────────────────────────────────────
function openForm(name) {
  ['send','delete','share'].forEach(n => {
    document.getElementById(`form-${n}`).classList.remove('open');
  });
  document.getElementById(`form-${name}`).classList.add('open');
  document.getElementById(`card-${name}`).scrollIntoView({behavior:'smooth', block:'nearest'});
}

function closeForm(name) {
  document.getElementById(`form-${name}`).classList.remove('open');
}

['send','delete','share'].forEach(name => {
  const card = document.getElementById(`card-${name}`);
  card.addEventListener('click', e => {
    if (!e.target.closest('.action-form')) openForm(name);
  });
});

// ─────────────────────────────────────────────
//  SUBMIT ACTION
// ─────────────────────────────────────────────
let pendingAction = null;
let countdownTimer = null;
let logCount = 0;
let statTotal = 0, statBlocked = 0, statPanic = 0;

function submitAction(action) {
  behavior.recordAttempt(action);

  let params = {};
  if (action === 'send') {
    params.recipient = document.getElementById('send-recipient').value || 'Unknown';
    params.amount = document.getElementById('send-amount').value || 0;
    params.detail = `₹${params.amount} → ${params.recipient}`;
  } else if (action === 'delete') {
    params.fileName = document.getElementById('delete-file').value || 'Unnamed file';
    params.fileType = document.getElementById('delete-type').value;
    params.detail = `${params.fileName} (${params.fileType})`;
  } else if (action === 'share') {
    params.dataType = document.getElementById('share-datatype').value;
    params.recipient = document.getElementById('share-recipient').value || 'External';
    params.detail = `${params.dataType} → ${params.recipient}`;
  }

  const risk = calcRisk(action, params);
  pendingAction = { action, params, risk };

  updateRiskUI(risk);
  showModal(action, params, risk);
}

// ─────────────────────────────────────────────
//  RISK UI UPDATE
// ─────────────────────────────────────────────
function updateRiskUI(risk) {
  const num = document.getElementById('risk-num');
  const bar = document.getElementById('risk-bar');
  const badge = document.getElementById('risk-badge');

  num.textContent = risk.total;

  const colors = { low: 'var(--low)', medium: 'var(--medium)', high: 'var(--high)' };
  num.style.color = colors[risk.level];
  bar.style.width = risk.total + '%';
  bar.style.background = colors[risk.level];

  badge.className = `risk-badge ${risk.level}`;
  badge.textContent = risk.level.toUpperCase();

  document.getElementById('rb-action').textContent = `+${risk.actionScore}`;
  document.getElementById('rb-amount').textContent = `+${risk.amountScore}`;
  document.getElementById('rb-behavior').textContent = `+${risk.behaviorScore}`;
  document.getElementById('rb-panic').textContent = `+${risk.panicPenalty}`;
}

// ─────────────────────────────────────────────
//  MODAL
// ─────────────────────────────────────────────
const ACTION_LABELS = {
  send: 'Send Money', delete: 'Delete File', share: 'Share Sensitive Info'
};

const MODAL_CONFIG = {
  low: {
    icon: '✅',
    title: 'Action Ready',
    color: 'var(--low)',
    body: (a, p) => `<strong>${ACTION_LABELS[a]}</strong>: ${p.detail}<br/><br/>
      Risk level is <strong>LOW</strong>. This action will proceed immediately.`,
    delay: 0
  },
  medium: {
    icon: '⚠️',
    title: 'Warning — Please Confirm',
    color: 'var(--medium)',
    body: (a, p) => `<strong>${ACTION_LABELS[a]}</strong>: ${p.detail}<br/><br/>
      Risk level is <strong>MEDIUM</strong>. This action may have significant consequences.
      Are you sure you want to proceed?`,
    delay: 0
  },
  high: {
    icon: '🚨',
    title: 'High Risk — Mandatory Delay',
    color: 'var(--high)',
    body: (a, p) => `<strong>${ACTION_LABELS[a]}</strong>: ${p.detail}<br/><br/>
      Risk level is <strong>HIGH</strong>. Behavior signals suggest possible panic or urgency.
      You must wait before proceeding.`,
    delay: 5
  }
};

function showModal(action, params, risk) {
  const cfg = MODAL_CONFIG[risk.level];

  document.getElementById('modal-icon').textContent = cfg.icon;
  document.getElementById('modal-title').textContent = cfg.title;
  document.getElementById('modal-body').innerHTML = cfg.body(action, params);

  const fillEl = document.getElementById('modal-risk-fill');
  fillEl.style.width = risk.total + '%';
  const colors = { low: 'var(--low)', medium: 'var(--medium)', high: 'var(--high)' };
  fillEl.style.background = colors[risk.level];

  const confirmBtn = document.getElementById('modal-confirm');
  const ring = document.getElementById('countdown-ring');

  if (cfg.delay > 0) {
    ring.style.display = 'block';
    confirmBtn.disabled = true;
    startCountdown(cfg.delay, confirmBtn);
  } else {
    ring.style.display = 'none';
    confirmBtn.disabled = false;
  }

  document.getElementById('overlay').classList.add('open');
}

function startCountdown(seconds, btn) {
  const numEl = document.getElementById('countdown-num');
  const ringFill = document.getElementById('ring-fill');
  const circumference = 220;

  let remaining = seconds;
  numEl.textContent = remaining;
  ringFill.style.strokeDashoffset = 0;

  if (countdownTimer) clearInterval(countdownTimer);

  countdownTimer = setInterval(() => {
    remaining--;
    numEl.textContent = remaining;
    const progress = (seconds - remaining) / seconds;
    ringFill.style.strokeDashoffset = circumference * progress;

    if (remaining <= 0) {
      clearInterval(countdownTimer);
      countdownTimer = null;
      btn.disabled = false;
    }
  }, 1000);
}

function dismissModal(result) {
  document.getElementById('overlay').classList.remove('open');
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }

  if (!pendingAction) return;
  const { action, params, risk } = pendingAction;
  pendingAction = null;

  const outcome = result === 'confirm' ? (risk.level === 'high' ? 'delayed' : 'allowed') : 'blocked';

  // Update stats
  statTotal++;
  document.getElementById('stat-total').textContent = statTotal;
  if (outcome === 'delayed') {
    statBlocked++;
    document.getElementById('stat-blocked').textContent = statBlocked;
  }
  if (behavior.isPanic) {
    statPanic++;
    document.getElementById('stat-panic').textContent = statPanic;
  }

  // Add to log
  addLog(action, params, risk, outcome);

  closeForm(action);

  if (result === 'confirm') {
    showToast(`✓ ${ACTION_LABELS[action]} — ${outcome.toUpperCase()}`, false);
  } else {
    showToast(`✗ Action cancelled by user.`, true);
  }
}

// ─────────────────────────────────────────────
//  LOG
// ─────────────────────────────────────────────
function addLog(action, params, risk, outcome) {
  logCount++;
  document.getElementById('log-empty').style.display = 'none';
  const table = document.getElementById('log-table');
  table.style.display = 'table';

  const now = new Date();
  const time = now.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'});

  const mlClass = behavior.mlClass;
  const panicFlag = behavior.isPanic;

  const outcomeTag = {
    allowed: `<span class="tag allowed">Allowed</span>`,
    delayed: `<span class="tag delayed">Delayed</span>`,
    blocked: `<span class="tag blocked">Blocked</span>`
  }[outcome];

  const row = document.createElement('tr');
  row.innerHTML = `
    <td style="color:var(--muted); font-family:'Space Mono',monospace;">#${logCount}</td>
    <td style="font-family:'Space Mono',monospace; color:var(--muted); font-size:11px">${time}</td>
    <td style="font-weight:700">${ACTION_LABELS[action]}</td>
    <td style="color:var(--muted); max-width:180px; overflow:hidden; text-overflow:ellipsis">${params.detail}</td>
    <td style="font-family:'Space Mono',monospace; color:${risk.level==='high'?'var(--high)':risk.level==='medium'?'var(--medium)':'var(--low)'}; font-weight:700">${risk.total}</td>
    <td><span class="tag ${risk.level}">${risk.level.toUpperCase()}</span></td>
    <td><span class="tag ${panicFlag?'panic':'normal'}">${panicFlag?'YES':'NO'}</span></td>
    <td style="font-family:'Space Mono',monospace; font-size:11px; color:var(--accent2)">${mlClass}</td>
    <td>${outcomeTag}</td>
  `;

  const tbody = document.getElementById('log-body');
  tbody.prepend(row);
}

// ─────────────────────────────────────────────
//  TOAST
// ─────────────────────────────────────────────
let toastTimer = null;
function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (isError ? ' error' : '');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.classList.remove('show'); }, 3000);
}

// Close overlay on backdrop click
document.getElementById('overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('overlay')) dismissModal('cancel');
});
