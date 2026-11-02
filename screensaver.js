/* Spořič obrazovky: při otevření aplikace se přehraje smyčka assets/intro/intro.mp4 (na výšku intro-portrait.mp4)
   a vrací se po 30 s nečinnosti. Dotyk ho skryje. Ručně: Více → Spořič obrazovky (window.FloraSaver.show(true)).
   Když prohlížeč zakáže automatické přehrání, zůstane zobrazený úvodní snímek s výzvou k dotyku. */
(function () {
  const IDLE_MS = 30000;
  const saver = document.createElement('div');
  saver.id = 'screensaver'; saver.hidden = true; saver.setAttribute('role', 'button'); saver.setAttribute('aria-label', 'Spořič obrazovky – dotkněte se pro pokračování');
  saver.innerHTML = '<video muted loop playsinline autoplay preload="auto"></video><span class="screensaver-hint">☝ Dotkněte se obrazovky</span><span class="screensaver-brand">Neoficiální prototyp · data ocflora.cz</span>';
  document.body.append(saver);
  const video = saver.querySelector('video');
  let idleSince = Date.now();
  // ?video=vyska | ?video=sirka přibije variantu pro panely, které hlásí špatnou orientaci (uloží se v zařízení).
  const forced = new URLSearchParams(location.search).get('video');
  try { if (forced === 'vyska' || forced === 'sirka') localStorage.setItem('flora-video', forced); if (forced === 'auto') localStorage.removeItem('flora-video'); } catch { /* ignore */ }
  function wantPortrait() { let saved = null; try { saved = localStorage.getItem('flora-video'); } catch { /* ignore */ } return saved ? saved === 'vyska' : innerHeight > innerWidth; }
  function pickSource() {
    const name = wantPortrait() ? 'intro-portrait' : 'intro';
    if (video.dataset.name === name) return;
    video.dataset.name = name; video.poster = `assets/intro/${name}-poster.jpg`;
    // MP4 (H.264) pro běžné prohlížeče a Safari, WebM (VP9) pro Chromium bez proprietárních kodeků.
    video.innerHTML = `<source src="assets/intro/${name}.webm" type="video/webm"><source src="assets/intro/${name}.mp4" type="video/mp4">`;
    video.load();
    if (!saver.hidden) video.play().catch(() => {});
  }
  function show(manual) {
    if (!saver.hidden) return;
    pickSource(); saver.hidden = false; saver.classList.toggle('is-manual', !!manual); video.currentTime = 0;
    video.play().catch(() => { /* autoplay zakázán: zůstane plakát s výzvou k dotyku */ });
  }
  function hide() { if (saver.hidden) return; saver.hidden = true; video.pause(); idleSince = Date.now(); }
  saver.addEventListener('click', (e) => { e.stopPropagation(); hide(); });
  for (const type of ['pointerdown', 'keydown', 'input', 'scroll', 'touchstart']) document.addEventListener(type, () => { if (saver.hidden) idleSince = Date.now(); }, true);
  document.addEventListener('keydown', hide);
  addEventListener('resize', () => { if (!saver.hidden) pickSource(); });
  setInterval(() => { if (saver.hidden && Date.now() - idleSince > IDLE_MS && !document.hidden) show(false); }, 1000);
  document.addEventListener('visibilitychange', () => { if (document.hidden) hide(); else idleSince = Date.now(); });
  window.FloraSaver = { show, hide, IDLE_MS, idle: () => Date.now() - idleSince };
  show(false); // první, co návštěvník uvidí
})();
