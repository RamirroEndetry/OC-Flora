/* Dotyková klávesnice pro infopanely a kiosky bez systémové klávesnice.
   Ukotví se dole a píše do naposledy aktivního textového pole (hledání, nákupní seznam, místo parkování).
   Bez háčků a čárek – hledání v aplikaci diakritiku nerozlišuje.
   Režim: auto (zobrazí se na obrazovkách od 900 px), on, off – Více → Dotyková klávesnice, nebo ?klavesnice=on|off|auto. */
(function () {
  const ROWS = ['1234567890', 'QWERTZUIOP', 'ASDFGHJKL', 'YXCVBNM'];
  const KEY = 'flora-kbd';
  const big = matchMedia('(min-width: 900px)');
  let mode = 'auto', target = null, shift = false, lower = true; // malá písmena, Shift = velké
  try { mode = localStorage.getItem(KEY) || 'auto'; } catch { /* ignore */ }
  const forced = new URLSearchParams(location.search).get('klavesnice');
  if (['on', 'off', 'auto'].includes(forced)) { mode = forced; try { localStorage.setItem(KEY, mode); } catch { /* ignore */ } }

  const dock = document.createElement('div');
  dock.id = 'kbd'; dock.hidden = true; dock.setAttribute('aria-label', 'Dotyková klávesnice');
  document.body.append(dock);

  function letter(c) { return /[A-Z]/.test(c) ? (lower && !shift ? c.toLowerCase() : c) : c; }
  function markup() {
    const last = ROWS.length - 1;
    return `<div class="kbd__head"><span class="kbd__title">⌨ Klávesnice</span><span class="kbd__target" id="kbdTarget"></span><button type="button" class="kbd__close" data-key="close" aria-label="Skrýt klávesnici">✕</button></div>
      ${ROWS.map((row, i) => `<div class="kbd__row">${i === last ? `<button type="button" class="kbd__key kbd__key--wide kbd__key--fn" data-key="shift" aria-pressed="${shift}" aria-label="Velká písmena">⇧</button>` : ''}${[...row].map((c) => `<button type="button" class="kbd__key" data-key="${letter(c)}">${letter(c)}</button>`).join('')}${i === 0 ? '<button type="button" class="kbd__key kbd__key--wide kbd__key--fn" data-key="backspace" aria-label="Smazat znak">⌫</button>' : ''}${i === last ? '<button type="button" class="kbd__key kbd__key--fn" data-key="-">-</button><button type="button" class="kbd__key kbd__key--fn" data-key=".">.</button>' : ''}</div>`).join('')}
      <div class="kbd__row kbd__row--bottom"><button type="button" class="kbd__key kbd__key--fn kbd__key--wide" data-key="clear">Smazat vše</button><button type="button" class="kbd__key kbd__key--space" data-key=" " aria-label="Mezera">mezera</button><button type="button" class="kbd__key kbd__key--go kbd__key--wide" data-key="enter">Hotovo</button></div>`;
  }
  function typeable(el) { return !!(el && el.matches && el.matches('input[type=text],input[type=search],input:not([type])') && !el.readOnly && !el.disabled && !el.closest('#kbd')); }
  function enabled() { return mode === 'on' || (mode === 'auto' && big.matches); }
  function label(el) { return el.getAttribute('aria-label') || el.placeholder || 'Aktivní pole'; }

  function update() {
    const live = target && target.isConnected && typeable(target);
    const visible = enabled() && live;
    if (visible && !dock.innerHTML) dock.innerHTML = markup();
    dock.hidden = !visible;
    document.body.classList.toggle('kbd-open', visible);
    if (visible) { const t = document.getElementById('kbdTarget'); if (t) t.textContent = label(target); }
  }
  function redraw() { if (!dock.hidden) { dock.innerHTML = markup(); update(); } }
  /* Prázdné pole začíná velkým písmenem, pak se píše malými. */
  function autoShift(input) { const want = !input.value.length; if (want !== shift) { shift = want; redraw(); } }

  function press(key) {
    if (key === 'close') { target = null; update(); return; }
    const input = target; if (!input || !input.isConnected) { update(); return; }
    if (key === 'shift') { shift = !shift; redraw(); return; }
    if (key === 'enter') {
      const form = input.form;
      if (form) form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      else input.blur();
      if (!form) { target = null; update(); }
      return;
    }
    const start = input.selectionStart ?? input.value.length, end = input.selectionEnd ?? input.value.length;
    let v = input.value, caret = start;
    if (key === 'backspace') { if (start !== end) { v = v.slice(0, start) + v.slice(end); } else if (start > 0) { v = v.slice(0, start - 1) + v.slice(end); caret = start - 1; } }
    else if (key === 'clear') { v = ''; caret = 0; }
    else { const ch = /[A-Z]/.test(key) && !shift && lower ? key.toLowerCase() : key; v = v.slice(0, start) + ch + v.slice(end); caret = start + ch.length; if (shift) { shift = false; redraw(); } }
    input.value = v;
    try { input.setSelectionRange(caret, caret); } catch { /* search inputs */ }
    autoShift(input);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.focus({ preventScroll: true });
  }

  dock.addEventListener('pointerdown', (e) => e.preventDefault()); // neodebrat fokus z pole
  dock.addEventListener('click', (e) => { const k = e.target.closest('[data-key]'); if (k) press(k.dataset.key); });
  document.addEventListener('focusin', (e) => {
    if (!typeable(e.target)) return;
    target = e.target; shift = !target.value.length; update();
    if (!dock.hidden) setTimeout(() => target && target.scrollIntoView({ block: 'center', behavior: 'smooth' }), 50);
  });
  // Po překreslení obrazovky zmizí i pole – skrýt klávesnici.
  new MutationObserver(() => { if (target && !target.isConnected) { target = null; update(); } }).observe(document.getElementById('view') || document.body, { childList: true, subtree: true });
  // Když je klávesnice zapnutá, systémovou klávesnici potlačit (inputmode=none).
  function applyInputMode() { document.querySelectorAll('#view input[type=text],#view input[type=search],#view input:not([type])').forEach((el) => { if (enabled()) { if (!el.dataset.im) el.dataset.im = el.getAttribute('inputmode') || 'text'; el.setAttribute('inputmode', 'none'); } else if (el.dataset.im) { el.setAttribute('inputmode', el.dataset.im); delete el.dataset.im; } }); }
  new MutationObserver(applyInputMode).observe(document.getElementById('view') || document.body, { childList: true, subtree: true });
  applyInputMode();
  big.addEventListener('change', () => { applyInputMode(); update(); });

  window.FloraKeyboard = {
    mode: () => mode,
    setMode(m) { mode = m; try { localStorage.setItem(KEY, m); } catch { /* ignore */ } applyInputMode(); update(); },
    show(el) { if (typeable(el)) { target = el; shift = !el.value.length; el.focus({ preventScroll: true }); update(); } },
    hide() { target = null; update(); },
  };
})();
