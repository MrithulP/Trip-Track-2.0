// TripTrack — front-end logic

// ---------- data ----------
const CATS = {
  Food:       { emoji: '🍜', color: '#f7c444', label: 'Food & Drink' },
  Travel:     { emoji: '🚌', color: '#7c6af7', label: 'Travel & Transport' },
  Stay:       { emoji: '🏕', color: '#38d1d1', label: 'Stay & Lodging' },
  Activities: { emoji: '🧗', color: '#2dd4a0', label: 'Activities & Entry' },
  Shopping:   { emoji: '🛍', color: '#e96bbf', label: 'Shopping' },
  Medical:    { emoji: '💊', color: '#f25f5f', label: 'Medical & Safety' },
  Fuel:       { emoji: '⛽', color: '#f07a4a', label: 'Fuel' },
  Other:      { emoji: '📦', color: '#7878a0', label: 'Other' },
};
const CURRENCIES = [['₹', 'INR'], ['$', 'USD'], ['€', 'EUR'], ['£', 'GBP'], ['¥', 'JPY']];
const KEY = 'triptrack_v2'; // same key as before, so saved trips keep working

const blank = () => ({ budget: 0, expenses: [], tripName: '', currency: { sym: '₹', code: 'INR' }, days: 1, locked: false });

function load() {
  try { return { ...blank(), ...JSON.parse(localStorage.getItem(KEY)) }; }
  catch { return blank(); }
}

let state = load();
let activeFilter = 'All';
let pendingDeleteId = null;
let adjustInc = true;

// ---------- tiny helpers ----------
const $ = id => document.getElementById(id);
const set = (id, text) => { $(id).textContent = text; };
const save = () => localStorage.setItem(KEY, JSON.stringify(state));
const num = n => Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
const fmt = n => state.currency.sym + num(n);
const cat = c => CATS[c] || CATS.Other;
const total = () => state.expenses.reduce((s, e) => s + e.amount, 0);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// [[category, amount], ...] biggest first
function catTotals() {
  const t = {};
  state.expenses.forEach(e => { t[e.cat] = (t[e.cat] || 0) + e.amount; });
  return Object.entries(t).sort((a, b) => b[1] - a[1]);
}

function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove('show'), 2200);
}

const openModal = id => $(id).classList.add('open');
const closeModal = id => $(id).classList.remove('open');
document.querySelectorAll('.modal-bg').forEach(bg =>
  bg.addEventListener('click', e => { if (e.target === bg) bg.classList.remove('open'); }));

// ---------- trip setup ----------
function setCurrency(c) {
  state.currency = c;
  document.querySelectorAll('.currency-opt').forEach(el => el.classList.toggle('sel', el.dataset.code === c.code));
  document.querySelectorAll('.prefix').forEach(el => { el.textContent = c.sym; });
}

function selCurrency(el) {
  if (state.locked) return;
  setCurrency({ sym: el.dataset.sym, code: el.dataset.code });
  renderAll();
}

function applyLockState() {
  ['budgetInput', 'tripNameInput', 'tripDaysInput'].forEach(id => { $(id).disabled = state.locked; });
  $('lockBtn').hidden = state.locked;
  $('adjustRow').hidden = !state.locked;
  $('budgetInput').value = state.budget || '';
  $('tripNameInput').value = state.tripName;
  $('tripDaysInput').value = state.days || '';
  setCurrency(state.currency);
}

function lockBudget() {
  const name = $('tripNameInput').value.trim();
  const budget = Number($('budgetInput').value);
  if (!name) return toast('Enter a trip name');
  if (budget <= 0) return toast('Enter a valid budget');

  Object.assign(state, { tripName: name, budget, days: Number($('tripDaysInput').value) || 1, locked: true });
  save(); applyLockState(); renderAll();
  toast('Trip locked! Have a great expedition ✈');
}

function openAdjust(inc) {
  adjustInc = inc;
  set('adjustTitle', inc ? 'Increase Budget' : 'Decrease Budget');
  set('adjustDesc', inc ? 'Add extra funds to your trip budget.' : 'Reduce your available budget.');
  $('adjustInput').value = '';
  openModal('adjustBG');
}

function confirmAdjust() {
  const v = Number($('adjustInput').value);
  if (v <= 0) return toast('Enter a valid amount');
  if (!adjustInc && v > state.budget) return toast('Not enough budget');

  state.budget += adjustInc ? v : -v;
  $('budgetInput').value = state.budget;
  save(); renderAll(); closeModal('adjustBG');
  toast(`Budget ${adjustInc ? 'increased' : 'reduced'} by ${fmt(v)}`);
}

function openSettings() {
  $('settingsTripName').value = state.tripName;
  $('settingsDays').value = state.days;
  openModal('settingsBG');
}

function saveSettings() {
  const name = $('settingsTripName').value.trim();
  if (!name) return toast('Enter a trip name');

  state.tripName = name;
  state.days = Number($('settingsDays').value) || 1;
  save(); applyLockState(); renderAll(); closeModal('settingsBG');
  toast('Settings saved');
}

function resetTrip() {
  state = blank();
  localStorage.removeItem(KEY);
  activeFilter = 'All';
  markTabs(); applyLockState(); renderAll(); closeModal('resetBG');
  toast('Trip reset. Ready for a new adventure!');
}

// ---------- expenses ----------
function addExpense() {
  if (!state.locked) return toast('Lock your budget first');
  const name = $('expName').value.trim();
  const amount = Number($('expAmt').value);
  if (!name || amount <= 0) return toast('Enter a valid name and amount');

  state.expenses.unshift({
    id: Date.now(), name, amount,
    cat: $('expCat').value,
    day: Number($('expDay').value) || 1,
    note: $('expNote').value.trim(),
    ts: new Date().toISOString(),
  });
  ['expName', 'expAmt', 'expNote'].forEach(id => { $(id).value = ''; });
  save(); renderAll();
  toast('Expense added');
}

function openDelete(id) {
  pendingDeleteId = id;
  const e = state.expenses.find(x => x.id === id);
  set('deleteDesc', `Remove "${e.name}" (${fmt(e.amount)})?`);
  openModal('deleteBG');
}

function confirmDelete() {
  state.expenses = state.expenses.filter(x => x.id !== pendingDeleteId);
  save(); renderAll(); closeModal('deleteBG');
  toast('Expense removed');
}

function setFilter(name) {
  activeFilter = name;
  markTabs();
  renderExpenses();
}

const markTabs = () => document.querySelectorAll('.tab').forEach(t =>
  t.classList.toggle('active', t.dataset.filter === activeFilter));

// ---------- rendering ----------
function renderAll() { renderStats(); renderCats(); renderExpenses(); }

function renderStats() {
  const spent = total(), n = state.expenses.length;
  const left = state.budget - spent;
  const pct = state.budget > 0 ? Math.min(spent / state.budget * 100, 100) : 0;
  const days = Math.max(state.days, 1);
  const dayNow = Math.min(Math.max(1, ...state.expenses.map(e => e.day || 1)), days);
  const top = catTotals()[0];

  set('totalSpentVal', num(spent));
  set('totalSpentSub', `${n} expense${n !== 1 ? 's' : ''}`);

  set('remainingVal', num(Math.abs(left)));
  $('remainingVal').className = 'stat-val ' + (left >= 0 ? 'green' : 'red');
  set('remainingSub', left < 0 ? 'OVER BUDGET' : `of ${fmt(state.budget)} budget`);

  set('dailyAvgVal', n ? num(spent / dayNow) : '—');
  set('dailyAvgSub', `day ${dayNow} of ${days}`);

  set('topCatVal', top ? `${cat(top[0]).emoji} ${top[0]}` : '—');
  set('topCatSub', top ? fmt(top[1]) : 'no expenses yet');

  const fill = $('budgetFill');
  fill.style.width = pct + '%';
  fill.style.background = pct < 70 ? 'var(--green)' : pct < 90 ? 'var(--amber)' : 'var(--red)';
  set('barSpentLabel', `Spent: ${fmt(spent)}`);
  set('barPctLabel', `${Math.round(pct)}% used`);
  set('barBudgetLabel', `Budget: ${fmt(state.budget)}`);
  set('tripNameDisplay', state.tripName || 'No trip set');
}

function renderCats() {
  const rows = catTotals(), all = total();
  $('catList').innerHTML = rows.length
    ? rows.map(([c, amt]) => {
        const { emoji, color } = cat(c);
        return `<div class="cat-row">
          <div class="cat-dot" style="background:${color}"></div>
          <div class="cat-name">${emoji} ${c}</div>
          <div class="cat-bar-wrap"><div class="cat-bar-fill" style="width:${amt / all * 100}%;background:${color}"></div></div>
          <div class="cat-amt" style="color:${color}">${fmt(amt)}</div>
        </div>`;
      }).join('')
    : '<div class="cat-empty">No expenses yet</div>';
}

function expenseRow(e) {
  const { emoji, color } = cat(e.cat);
  return `<div class="expense-item">
    <div class="exp-cat-icon" style="background:${color}22">${emoji}</div>
    <div class="exp-info">
      <div class="exp-name">${esc(e.name)}</div>
      <div class="exp-meta">${esc(e.cat)}${e.note ? ' · ' + esc(e.note) : ''}</div>
    </div>
    <div class="exp-right">
      <div class="exp-amt" style="color:${color}">${fmt(e.amount)}</div>
      <button class="del-btn" onclick="openDelete(${e.id})">✕</button>
    </div>
  </div>`;
}

function renderExpenses() {
  const all = activeFilter === 'All';
  const list = all ? state.expenses : state.expenses.filter(e => e.cat === activeFilter);

  if (!list.length) {
    $('expenseList').innerHTML = `<div class="empty-state">
      <div class="empty-icon">${all ? '📋' : cat(activeFilter).emoji}</div>
      <div>${all ? 'No expenses logged yet' : `No ${activeFilter} expenses`}</div>
    </div>`;
    return;
  }

  const byDay = {};
  list.forEach(e => { const d = e.day || 1; (byDay[d] = byDay[d] || []).push(e); });

  $('expenseList').innerHTML = Object.keys(byDay).sort((a, b) => b - a).map(day => {
    const items = byDay[day];
    const dayTotal = items.reduce((s, e) => s + e.amount, 0);
    return `<div class="day-badge">Day ${day} · ${fmt(dayTotal)}</div>` + items.map(expenseRow).join('');
  }).join('');
}

// ---------- export + Python analysis ----------
function exportTrip() {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' }));
  a.download = 'triptrack_export.json';
  a.click();
  URL.revokeObjectURL(a.href);
  toast('Trip exported');
}

async function analyzeTrip() {
  if (!state.expenses.length) return toast('Add some expenses first');
  const btn = $('analyzeBtn');
  btn.disabled = true;
  btn.textContent = 'Analyzing…';
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state),
    });
    if (!res.ok) throw new Error('bad response');
    renderAnalysis(await res.json());
  } catch {
    $('analysisOut').innerHTML = '<div class="an-note">Analysis needs the Python server. Run <b>python app.py</b> and open the app from http://127.0.0.1:5000.</div>';
  }
  btn.disabled = false;
  btn.textContent = 'Re-run Analysis';
}

function renderAnalysis({ stats, forecast, insights, charts }) {
  const mini = (label, value, cls = '') =>
    `<div class="stat-card mini"><div class="stat-label">${label}</div><div class="stat-val ${cls}">${value}</div></div>`;

  $('analysisOut').innerHTML = `
    <div class="an-grid">
      ${mini('Avg expense', fmt(stats.mean))}
      ${mini('Median', fmt(stats.median))}
      ${mini('Std deviation', fmt(stats.std))}
      ${mini('Projected total', forecast.has_forecast ? fmt(forecast.projected_total) : '—', forecast.over_budget ? 'red' : 'green')}
    </div>
    ${insights.map(t => `<div class="an-insight ${/over budget|Unusually/.test(t) ? 'warn' : ''}">${esc(t)}</div>`).join('')}
    <img class="an-chart" alt="Spending by category" src="data:image/png;base64,${charts.category}">
    <img class="an-chart" alt="Spend trend and forecast" src="data:image/png;base64,${charts.trend}">
    <div class="an-note">Computed in Python: numpy · scikit-learn · matplotlib</div>`;
}

// ---------- start up ----------
$('expCat').innerHTML = Object.entries(CATS).map(([k, c]) => `<option value="${k}">${c.emoji} ${c.label}</option>`).join('');

$('filterTabs').innerHTML = ['All', ...Object.keys(CATS)].map(k =>
  `<div class="tab" data-filter="${k}" onclick="setFilter('${k}')">${k === 'All' ? 'All' : CATS[k].emoji + ' ' + k}</div>`).join('');

$('currencyRow').innerHTML = CURRENCIES.map(([s, c]) =>
  `<div class="currency-opt" data-sym="${s}" data-code="${c}" onclick="selCurrency(this)">${s} ${c}</div>`).join('');

markTabs();
applyLockState();
renderAll();

if ('serviceWorker' in navigator) navigator.serviceWorker.register('service-worker.js');
