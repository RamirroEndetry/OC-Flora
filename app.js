/* OC Flora – průvodce centrem (prototyp). Vanilla JS, hash routing, data v data.js. */
(() => {
  'use strict';
  const D = window.FLORA_DATA;
  const $ = (sel, root = document) => root.querySelector(sel);
  const view = $('#view');
  const DAYS = ['Ne', 'Po', 'Út', 'St', 'Čt', 'Pá', 'So']; // Date.getDay()
  const DAYS_LONG = ['neděle', 'pondělí', 'úterý', 'středa', 'čtvrtek', 'pátek', 'sobota'];
  const MONTHS = ['ledna', 'února', 'března', 'dubna', 'května', 'června', 'července', 'srpna', 'září', 'října', 'listopadu', 'prosince'];
  const STORE_KEY = 'ocflora-app-v1';

  /* ---------- Úložiště ---------- */
  const state = Object.assign({ favs: [], parking: null, list: [], dismissed: [], theme: 'auto' }, load());
  function load() { try { return JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); } catch { return {}; } }
  function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch { /* soukromý režim */ } }
  if (state.theme !== 'auto') document.documentElement.dataset.theme = state.theme;

  /* ---------- Čas (s možností simulace ?now=2026-11-02T18:40 pro testování) ---------- */
  let timeOffset = 0;
  (function initTime() {
    const m = location.search.match(/[?&]now=([^&]+)/);
    let sim = m ? decodeURIComponent(m[1]) : sessionStorage.getItem('flora-now');
    if (sim) {
      const t = new Date(sim);
      if (!isNaN(t)) { timeOffset = t.getTime() - Date.now(); sessionStorage.setItem('flora-now', sim); }
    }
  })();
  const now = () => new Date(Date.now() + timeOffset);
  const isSim = () => timeOffset !== 0;
  const isoDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const todayIso = () => isoDate(now());
  const fmtMin = (m) => `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}`;
  const fmtClock = (d) => `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
  const fmtDate = (iso) => { const [y, mo, da] = iso.split('-').map(Number); return `${da}. ${mo}. ${y}`; };
  const fmtDateLong = (iso) => { const [y, mo, da] = iso.split('-').map(Number); return `${da}. ${MONTHS[mo - 1]}`; };
  const weekIdx = (d) => (d.getDay() + 6) % 7; // Po=0 … Ne=6 (pořadí v datech)
  const minutesOfDay = (d) => d.getHours() * 60 + d.getMinutes();
  const dur = (mins) => { mins = Math.max(0, Math.round(mins)); const h = Math.floor(mins / 60), m = mins % 60; return h ? `${h} h ${String(m).padStart(2, '0')} min` : `${m} min`; };

  // Státní svátky ČR (obchody nad 200 m² mají ze zákona zavřeno jen o vybraných svátcích).
  const HOLIDAYS = {
    '2026-01-01': 1, '2026-04-03': 0, '2026-04-06': 1, '2026-05-01': 0, '2026-05-08': 1, '2026-07-05': 0, '2026-07-06': 0, '2026-09-28': 1, '2026-10-28': 1, '2026-11-17': 0, '2026-12-24': 2, '2026-12-25': 1, '2026-12-26': 1,
    '2027-01-01': 1, '2027-03-26': 0, '2027-03-29': 1, '2027-05-01': 0, '2027-05-08': 1, '2027-07-05': 0, '2027-07-06': 0, '2027-09-28': 1, '2027-10-28': 1, '2027-11-17': 0, '2027-12-24': 2, '2027-12-25': 1, '2027-12-26': 1,
  };
  const isHoliday = (d) => isoDate(d) in HOLIDAYS;
  const shopClosureHoliday = (d) => HOLIDAYS[isoDate(d)]; // 1 = celý den, 2 = od 12:00, 0 = běžný svátek

  /** Stav obchodů centra se zohledněním zákonného uzavření o svátcích */
  function shopsStatus(at = now()) {
    const week = D.center.hours.find((h) => h.id === 'obchody').week, hol = shopClosureHoliday(at);
    if (hol === 1 || (hol === 2 && minutesOfDay(at) >= 720)) return { open: false, holiday: true, cls: 'closed', label: 'Státní svátek – většina obchodů zavřeno', short: 'svátek, zavřeno' };
    const st = status(week, at);
    if (hol === 2 && st.open) return { ...st, label: 'Otevřeno do 12:00 (Štědrý den)', short: 'do 12:00' };
    return st;
  }
  /** Stav podle týdenních hodin: {open, soon, label, cls} */
  function status(week, at = now()) {
    if (!week || !week.some(Boolean)) return { open: false, cls: 'na', label: 'Hodiny neuvedeny', short: '' };
    const wi = weekIdx(at), mins = minutesOfDay(at), today = week[wi];
    if (today && mins >= today[0] && mins < today[1]) {
      const left = today[1] - mins;
      if (left <= 30) return { open: true, soon: true, cls: 'soon', label: `Zavírá za ${left} min`, short: `zavírá za ${left} min` };
      const close = today[1] === 1440 ? '24:00' : fmtMin(today[1]);
      return { open: true, cls: 'open', label: `Otevřeno do ${close}`, short: `do ${close}` };
    }
    if (today && mins < today[0]) {
      const wait = today[0] - mins;
      return { open: false, cls: 'closed', label: wait <= 60 ? `Otevírá za ${wait} min` : `Otevírá v ${fmtMin(today[0])}`, short: wait <= 60 ? `otevírá za ${wait} min` : `od ${fmtMin(today[0])}` };
    }
    for (let i = 1; i <= 7; i++) {
      const h = week[(wi + i) % 7];
      if (h) return { open: false, cls: 'closed', label: i === 1 ? `Zavřeno · zítra od ${fmtMin(h[0])}` : `Zavřeno · ${DAYS[(at.getDay() + i) % 7]} od ${fmtMin(h[0])}`, short: 'zavřeno' };
    }
    return { open: false, cls: 'closed', label: 'Zavřeno', short: 'zavřeno' };
  }
  const hoursText = (span) => (span ? `${fmtMin(span[0])}–${span[1] === 1440 ? '24:00' : fmtMin(span[1])}` : 'zavřeno');

  /* ---------- Pomocné ---------- */
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const icon = (id, cls = '') => `<svg class="${cls}" aria-hidden="true"><use href="#i-${id}"/></svg>`;
  const byId = Object.fromEntries(D.shops.map((s) => [s.id, s]));
  const catLabel = Object.fromEntries(D.cats.map((c) => [c.id, c.label]));
  const floorLabel = (n) => (n == null ? '?' : n < 0 ? `−${Math.abs(n)}` : String(n));
  const floorText = (n) => (n == null ? 'podlaží neuvedeno' : `${floorLabel(n)}. podlaží`);
  const isFav = (id) => state.favs.includes(id);
  const nameInitial = (name) => name.replace(/[^A-Za-zÀ-ž0-9&]/g, '').slice(0, 2).toUpperCase() || '•';
  function logoHtml(s, lg = false) {
    const dark = s.logoDark ? ' logo--dark' : '';
    if (!s.logo) return `<div class="logo ${lg ? 'logo--lg' : ''} logo--txt">${esc(nameInitial(s.name))}</div>`;
    return `<div class="logo ${lg ? 'logo--lg' : ''}${dark}"><img src="${s.logo}" alt="" loading="lazy" decoding="async" onerror="this.parentNode.classList.add('logo--txt');this.replaceWith(document.createTextNode('${esc(nameInitial(s.name))}'))"></div>`;
  }
  function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('is-on'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('is-on'), 2600); }
  function sanitizeUrl(u) { if (!u) return ''; if (/^\/\//.test(u)) return 'https:' + u; if (!/^https?:/i.test(u)) return 'https://' + u; return u; }
  const hostOf = (u) => { try { return new URL(sanitizeUrl(u)).host.replace(/^www\./, ''); } catch { return u; } };

  /* ---------- Nabídky a akce ---------- */
  function activeOffers() {
    const t = todayIso(), soon = isoDate(new Date(now().getTime() + 14 * 864e5));
    const recent = isoDate(new Date(now().getTime() - 45 * 864e5));
    return D.offers
      .filter((o) => (!o.to || o.to >= t) && (!o.from || o.from <= soon) && (o.to || o.from || o.date >= recent))
      .sort((a, b) => {
        const ea = a.to || '9999', eb = b.to || '9999';
        if (ea !== eb) return ea < eb ? -1 : 1;
        return b.date < a.date ? -1 : 1;
      });
  }
  function offerValidity(o) {
    const t = todayIso();
    if (o.from && o.from > t) return `Od ${fmtDate(o.from)}`;
    if (o.to) {
      if (o.to === t) return 'Platí jen dnes';
      const days = Math.round((new Date(o.to) - new Date(t)) / 864e5);
      return days <= 7 ? `Ještě ${days} ${days === 1 ? 'den' : days < 5 ? 'dny' : 'dní'}` : `Do ${fmtDate(o.to)}`;
    }
    return `Zveřejněno ${fmtDate(o.date)}`;
  }
  function eventState(n) {
    const t = todayIso();
    if (!n.start) return 'info';
    if (n.end && n.end < t) return 'past';
    if (!n.end && n.start < t) return n.kind === 'akce' ? 'live' : 'past';
    if (n.start <= t && (!n.end || n.end >= t)) return 'live';
    return 'upcoming';
  }
  function offerCard(o, wide = false) {
    const shop = o.shopId ? byId[o.shopId] : null;
    return `<a class="offer" href="#/nabidka/${o.id}" ${wide ? '' : ''}>
      <img class="offer__img" src="${esc(o.image)}" alt="" loading="lazy" decoding="async">
      <div class="offer__body">
        <div class="offer__shop">${esc(o.shop || 'OC Flora')}${shop && shop.floor != null ? ` · ${floorLabel(shop.floor)}. podl.` : ''}</div>
        <div class="offer__title">${esc(o.title)}</div>
        <div class="offer__valid">${esc(offerValidity(o))}</div>
      </div></a>`;
  }
  function eventCard(n) {
    const st = eventState(n), [, m, d] = (n.start || n.date).split('-');
    const label = st === 'live' ? (n.end === n.start ? 'Dnes' : 'Probíhá') : st === 'upcoming' ? 'Chystá se' : st === 'past' ? 'Proběhlo' : 'Info';
    return `<a class="event" href="#/akce/${n.id}">
      <div class="event__date ${st === 'live' ? 'event__date--live' : ''}"><b>${Number(d)}.</b><span>${MONTHS[Number(m) - 1].slice(0, 3)}</span></div>
      <div class="event__body">
        <div class="row row--wrap"><span class="badge ${st === 'live' ? 'badge--wine' : st === 'upcoming' ? 'badge--gold' : ''}">${label}</span>${n.time ? `<span class="tiny muted">${esc(n.time)}</span>` : ''}${n.place ? `<span class="tiny muted">· ${esc(n.place)}</span>` : ''}</div>
        <h3 style="margin-top:4px">${esc(n.title)}</h3>
        ${n.start && n.end && n.end !== n.start ? `<div class="tiny muted">${fmtDate(n.start)} – ${fmtDate(n.end)}</div>` : ''}
      </div></a>`;
  }

  /* ---------- Parkování ---------- */
  function freeMinutes(arrival, bonus) {
    const wd = arrival.getDay(), h = arrival.getHours() + arrival.getMinutes() / 60;
    const weekendLike = wd === 0 || wd === 6 || isHoliday(arrival);
    let free = !weekendLike && h >= 7 && h < 19 ? 60 : 180;
    if (bonus) free += D.parking.bonus;
    return free;
  }
  function parkingCalc(p, at = now()) {
    const arrival = new Date(p.arrivedAt);
    const elapsed = (at - arrival) / 60000;
    const free = freeMinutes(arrival, p.bonus);
    const over = elapsed - free;
    const paidHours = over > 0 ? Math.ceil(over / 60) : 0;
    const cost = paidHours * D.parking.rate;
    const nextIn = over <= 0 ? free - elapsed : paidHours * 60 - over; // minuty do dalšího zlomu
    return { arrival, elapsed, free, cost, paidHours, nextIn, freeUntil: new Date(arrival.getTime() + free * 60000) };
  }

  /* ---------- Router ---------- */
  const routes = {
    dnes: renderHome, obchody: renderShops, obchod: renderShop, jidlo: renderFood, parkovani: renderParking,
    mapa: renderMap, akce: renderEvents, nabidky: renderOffers, nabidka: renderOffer, vice: renderMore,
    oblibene: renderFavs, seznam: renderList, info: renderInfo, doprava: renderTransport, karta: renderGift, kino: renderCinema,
  };
  let currentQuery = {};
  function parseHash() {
    const raw = location.hash.replace(/^#\/?/, '') || 'dnes';
    const [path, qs = ''] = raw.split('?');
    const [route, ...rest] = path.split('/');
    const q = Object.fromEntries(new URLSearchParams(qs));
    return { route: routes[route] ? route : 'dnes', param: rest.join('/'), q };
  }
  function render() {
    const { route, param, q } = parseHash();
    currentQuery = q;
    clearInterval(render.tick);
    view.innerHTML = routes[route](param, q) || '';
    const tab = { obchod: 'obchody', nabidky: 'dnes', nabidka: 'dnes', akce: 'dnes', mapa: 'vice', oblibene: 'vice', seznam: 'vice', info: 'vice', doprava: 'vice', karta: 'vice', kino: 'vice' }[route] || route;
    document.querySelectorAll('.tabbar a').forEach((a) => (a.dataset.tab === tab ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current')));
    if (!render.keepScroll) window.scrollTo(0, 0);
    render.keepScroll = false;
    renderTopStatus();
    afterRender(route, param);
  }
  function renderTopStatus() {
    const st = shopsStatus();
    const d = now();
    $('#topStatus').innerHTML = `${isSim() ? '<span class="pill-time" title="Simulovaný čas pro testování">TEST ' + fmtClock(d) + '</span> ' : ''}${st.open && !st.soon ? `Obchody <b>${esc(st.short)}</b>` : `<b>${esc(st.label.split(' · ')[0])}</b>`}`;
  }
  window.addEventListener('hashchange', render);

  /* ---------- Obrazovky ---------- */
  function greeting() { const h = now().getHours(); return h < 10 ? 'Dobré ráno' : h < 18 ? 'Dobrý den' : 'Dobrý večer'; }

  function renderHome() {
    const d = now(), t = todayIso();
    const st = shopsStatus();
    const live = D.news.filter((n) => eventState(n) === 'live' && n.kind !== 'doprava');
    const upcoming = D.news.filter((n) => eventState(n) === 'upcoming');
    const offers = activeOffers();
    const favs = state.favs.map((id) => byId[id]).filter(Boolean);
    const lateOpen = D.shops.filter((s) => { const h = s.hours[weekIdx(d)]; return h && h[1] > 1260 && !s.tags.includes('box'); });
    const hol = shopClosureHoliday(d);
    const parking = state.parking ? parkingCalc(state.parking) : null;
    const stale = parking && parking.elapsed > 18 * 60;
    const metro = D.transport.metroClosed;

    return `
      <section class="card card--wine">
        <div class="row">
          <div class="grow">
            <div class="small" style="opacity:.85">${greeting()} · ${DAYS_LONG[d.getDay()]} ${d.getDate()}. ${MONTHS[d.getMonth()]}</div>
            <h1 style="margin-top:4px">${st.holiday ? 'Dnes je státní svátek' : st.open ? 'Máme otevřeno' : 'Teď máme zavřeno'}</h1>
            <div class="small" style="margin-top:6px;opacity:.95">${esc(st.label)} · obchody Po–So 9–21, Ne 10–21</div>
          </div>
          <a class="iconbtn" href="#/info" aria-label="Otevírací doba celého centra" style="background:rgba(255,255,255,.18)">${icon('clock')}</a>
        </div>
        ${hol ? `<div class="notice small" style="margin-top:12px;background:rgba(255,255,255,.14);padding:10px;border-radius:12px">${icon('warn')}<div><b>Státní svátek.</b> ${hol === 2 ? 'Od 12:00 mají větší prodejny ze zákona zavřeno.' : 'Větší prodejny (nad 200 m²) mají ze zákona zavřeno.'} Menší obchody, restaurace a kino mohou být otevřené – ověřte si to u konkrétního místa.</div></div>` : ''}
      </section>

      ${stale ? `<a class="card card--warn" href="#/parkovani" style="display:flex;gap:12px;align-items:center;margin-top:12px;text-decoration:none;color:inherit">${icon('car')}<div class="grow"><b>Hlídání parkování z ${fmtDate(isoDate(parking.arrival))}</b> je stále zapnuté. Zapomněli jste ho ukončit?</div>${icon('chev')}</a>` : parking ? `<a class="card card--ok" href="#/parkovani" style="display:flex;gap:12px;align-items:center;margin-top:12px;text-decoration:none;color:inherit">${icon('car')}<div class="grow"><b>Zaparkováno ${dur(parking.elapsed)}</b> · ${parking.cost ? `aktuálně ${parking.cost} Kč` : `zdarma ještě ${dur(parking.nextIn)}`}${state.parking.level ? ` · úroveň ${esc(state.parking.level)}${state.parking.spot ? ', ' + esc(state.parking.spot) : ''}` : ''}</div>${icon('chev')}</a>` : ''}

      <section class="section">
        <div class="tiles">
          <a class="tile" href="#/obchody">${icon('bag')}Obchody</a>
          <a class="tile" href="#/jidlo">${icon('food')}Jídlo a káva</a>
          <a class="tile" href="#/parkovani">${icon('car')}Parkování</a>
          <a class="tile" href="#/mapa">${icon('map')}Plán centra</a>
          <a class="tile" href="#/kino">${icon('film')}Kino</a>
          <a class="tile" href="#/karta">${icon('gift')}Dárková karta</a>
        </div>
      </section>

      ${live.length || upcoming.length ? `<section class="section"><div class="section__head"><h2>Dnes v centru</h2><a href="#/akce">Všechny akce</a></div><div class="stack">${[...live, ...upcoming.slice(0, 2)].map(eventCard).join('')}</div></section>` : ''}

      ${!state.dismissed.includes('metro') && metro.until >= t ? `<section class="section"><div class="card card--warn notice">${icon('tram')}<div class="grow"><b>Metro Flora je uzavřené</b> (do ${fmtDate(metro.until)}). Tramvaje ${D.transport.trams.join(', ')} zastavují přímo u centra. <a href="#/doprava">Jak se k nám dostat</a></div><button class="iconbtn iconbtn--ink" style="width:36px;height:36px" data-dismiss="metro" aria-label="Skrýt upozornění">${icon('x')}</button></div></section>` : ''}

      ${offers.length ? `<section class="section"><div class="section__head"><h2>Aktuální nabídky</h2><a href="#/nabidky">Všechny (${offers.length})</a></div><div class="scroller">${offers.slice(0, 10).map((o) => offerCard(o)).join('')}</div></section>` : ''}

      ${favs.length ? `<section class="section"><div class="section__head"><h2>Moje oblíbené</h2><a href="#/oblibene">Spravovat</a></div><div class="list">${favs.slice(0, 5).map(shopRow).join('')}</div></section>` : `<section class="section"><div class="card card--tint small"><b>Tip:</b> U obchodu klepněte na hvězdičku a budete ho mít tady na úvodu i s aktuální otevírací dobou.</div></section>`}

      <section class="section"><div class="section__head"><h2>Otevřeno i po 21. hodině</h2></div><div class="list">${lateOpen.slice(0, 8).map(shopRow).join('')}</div><p class="tiny muted" style="margin-top:8px">Výdejní boxy (AlzaBox, Z-BOX, DHL, BENU) v −1. podlaží jsou přístupné denně 7:00–24:00.</p></section>

      <p class="tiny muted" style="margin-top:24px">Neoficiální prototyp. Data z ocflora.cz, stav k ${fmtDate(D.meta.updated)}. Otevírací doby jednotlivých prodejen se mohou lišit – rozhodující jsou informace přímo v centru.</p>`;
  }

  function shopRow(s) {
    const st = status(s.hours);
    return `<a class="shop" href="#/obchod/${s.id}">
      ${logoHtml(s)}
      <div class="shop__body">
        <div class="shop__name"><span>${esc(s.name)}</span>${isFav(s.id) ? `<span class="fav" aria-label="oblíbené">${icon('star')}</span>` : ''}</div>
        <div class="shop__meta"><span>${esc(catLabel[s.cat])}</span>${s.gift ? '<span class="badge badge--gold" title="Přijímá dárkovou kartu OC Flora">karta</span>' : ''}</div>
      </div>
      <div class="shop__right"><span class="floor" title="${floorText(s.floor)}">${floorLabel(s.floor)}</span><span class="status status--${st.cls} tiny">${esc(st.short)}</span></div>
    </a>`;
  }

  function renderShops(_, q) {
    const cat = q.cat || '', floor = q.floor || '', open = q.open === '1', gift = q.gift === '1', text = q.q || '';
    const chips = (items, key, cur) => items.map((c) => `<button class="chip" type="button" data-set="${key}" data-val="${c.id}" aria-pressed="${String(cur) === String(c.id)}">${esc(c.label)}</button>`).join('');
    return `
      <div class="page-head"><div class="grow"><h1>Obchody a služby</h1><p class="sub">${D.shops.length} míst · Po–So 9–21, Ne 10–21</p></div></div>
      <div class="sticky">
        <div class="search">${icon('search')}<input id="q" type="text" inputmode="search" placeholder="Hledat obchod, značku, službu…" value="${esc(text)}" autocomplete="off" enterkeyhint="search" aria-label="Hledat"><button class="iconbtn iconbtn--ink ${text ? '' : 'hidden'}" id="qClear" type="button" aria-label="Smazat">${icon('x')}</button></div>
        <div class="chips" style="margin-top:8px">
          <button class="chip" type="button" data-set="cat" data-val="" aria-pressed="${!cat}">Vše</button>
          ${chips(D.cats, 'cat', cat)}
        </div>
        <div class="chips">
          <button class="chip chip--small" type="button" data-toggle="open" aria-pressed="${open}">● Otevřeno teď</button>
          <button class="chip chip--small" type="button" data-toggle="gift" aria-pressed="${gift}">🎁 Dárková karta</button>
          <button class="chip chip--small" type="button" data-set="floor" data-val="" aria-pressed="${!floor}">Všechna patra</button>
          ${D.floors.map((f) => `<button class="chip chip--small" type="button" data-set="floor" data-val="${f.n}" aria-pressed="${floor === String(f.n)}">${f.label}. podl.</button>`).join('')}
        </div>
      </div>
      <div id="shopList" class="list" style="margin-top:8px"></div>`;
  }
  function filterShops(q) {
    const t = norm(q.q || '').trim();
    return D.shops.filter((s) => (!q.cat || s.cat === q.cat) && (!q.floor || String(s.floor) === q.floor) && (q.open !== '1' || status(s.hours).open) && (q.gift !== '1' || s.gift) && (!t || s.q.includes(t) || norm(s.name).includes(t)));
  }
  function renderShopList() {
    const q = currentQuery, list = filterShops(q), box = $('#shopList');
    if (!box) return;
    if (!list.length) { box.innerHTML = `<div class="empty">Nic jsme nenašli.<br><span class="small">Zkuste jiný výraz nebo zrušte filtry.</span></div>`; return; }
    const grouped = !q.q && !q.cat && !q.floor && q.open !== '1' && q.gift !== '1' && list.length > 20;
    let html = `<div class="tiny muted" style="margin:4px 4px 0">${list.length} ${list.length === 1 ? 'místo' : list.length < 5 ? 'místa' : 'míst'}</div>`;
    if (grouped) {
      let last = '';
      for (const s of list) { const L = norm(s.name)[0].toUpperCase(); if (L !== last) { html += `<div class="letter">${/[A-Z]/.test(L) ? L : '#'}</div>`; last = L; } html += shopRow(s); }
    } else html += list.map(shopRow).join('');
    box.innerHTML = html;
  }
  function setQuery(patch, replace = true) {
    const { route, param, q } = parseHash();
    const next = { ...q, ...patch };
    Object.keys(next).forEach((k) => (next[k] === '' || next[k] == null) && delete next[k]);
    const qs = new URLSearchParams(next).toString();
    render.keepScroll = true;
    const h = `#/${route}${param ? '/' + param : ''}${qs ? '?' + qs : ''}`;
    if (replace) history.replaceState(null, '', h); else location.hash = h;
    currentQuery = next;
  }

  function renderShop(id) {
    const s = byId[id];
    if (!s) return `<div class="empty">Obchod nenalezen. <a href="#/obchody">Zpět na seznam</a></div>`;
    const st = status(s.hours), wi = weekIdx(now());
    const offers = D.offers.filter((o) => o.shopId === s.id && activeOffers().includes(o));
    const floor = D.floors.find((f) => f.n === s.floor);
    return `
      <div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><p class="sub">${esc(catLabel[s.cat])}</p></div><button class="iconbtn iconbtn--ink" type="button" data-fav="${s.id}" aria-pressed="${isFav(s.id)}" aria-label="${isFav(s.id) ? 'Odebrat z oblíbených' : 'Přidat do oblíbených'}"><svg viewBox="0 0 24 24" style="${isFav(s.id) ? 'fill:var(--gold);color:var(--gold)' : ''}"><use href="#i-star"/></svg></button></div>
      <section class="card">
        <div class="detail__hero">${logoHtml(s, true)}<div class="grow"><h1>${esc(s.name)}</h1><div class="row row--wrap" style="margin-top:6px"><span class="status status--${st.cls}">${esc(st.label)}</span></div><div class="small muted" style="margin-top:4px">${icon('pin', 'ico')} ${floorText(s.floor)}${floor ? ` – ${esc(floor.name)}` : ''}</div></div></div>
        <div class="actions">
          ${s.phone ? `<a class="action" href="tel:${esc(s.phone.replace(/\s/g, ''))}">${icon('phone')}Zavolat</a>` : `<span class="action" aria-disabled="true" style="opacity:.45">${icon('phone')}Bez tel.</span>`}
          ${s.web ? `<a class="action" href="${esc(sanitizeUrl(s.web))}" target="_blank" rel="noopener">${icon('globe')}Web</a>` : `<span class="action" style="opacity:.45">${icon('globe')}Bez webu</span>`}
          <button class="action" type="button" data-showmap="${s.entity || ''}" ${s.entity ? '' : 'disabled'}>${icon('map')}Na plánu</button>
          <button class="action" type="button" data-addlist="${esc(s.name)}">${icon('list')}Do seznamu</button>
        </div>
      </section>
      <section class="card section">
        <h2>Otevírací doba</h2>
        <table class="hours" style="margin-top:8px">${s.hours.map((h, i) => `<tr class="${i === wi ? 'today' : ''}"><td>${['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle'][i]}${i === wi ? ' <span class="tiny">(dnes)</span>' : ''}</td><td>${hoursText(h)}</td></tr>`).join('')}</table>
        ${s.gift ? `<p class="small" style="margin:10px 0 0">🎁 Přijímá <a href="#/karta">dárkovou kartu OC Flora</a>.</p>` : '<p class="small muted" style="margin:10px 0 0">Dárkovou kartu OC Flora zde neuplatníte.</p>'}
      </section>
      <section id="mapbox" class="section hidden"><div class="card"><h2>Umístění na plánu</h2><p class="tiny muted">Interaktivní plán načítáme od provozovatele centra (Simplaq).</p><div id="mapframe"></div></div></section>
      ${s.desc ? `<section class="card section"><h2>O prodejně</h2><p class="desc" style="margin-top:8px">${esc(s.desc)}</p></section>` : ''}
      ${offers.length ? `<section class="section"><div class="section__head"><h2>Nabídky ${esc(s.name)}</h2></div><div class="grid">${offers.map((o) => offerCard(o, true)).join('')}</div></section>` : ''}
      <section class="section stack">
        ${s.email ? `<a class="btn btn--light btn--block" href="mailto:${esc(s.email)}">E-mail: ${esc(s.email)}</a>` : ''}
        <a class="btn btn--ghost btn--block" href="${esc(s.url)}" target="_blank" rel="noopener">${icon('external')} Stránka na ocflora.cz</a>
      </section>`;
  }

  function renderFood() {
    const q = currentQuery, tag = q.tag || '', openOnly = q.open === '1';
    const all = D.shops.filter((s) => s.cat === 'jidlo' || ['potraviny'].includes(s.cat) && s.tags.length);
    let list = all.filter((s) => (!tag || s.tags.includes(tag)) && (!openOnly || status(s.hours).open));
    list = list.sort((a, b) => Number(status(b.hours).open) - Number(status(a.hours).open) || norm(a.name).localeCompare(norm(b.name)));
    const fc = D.center.hours.find((h) => h.id === 'foodcourt'), fcSt = status(fc.week);
    return `
      <div class="page-head"><div class="grow"><h1>Jídlo a káva</h1><p class="sub">Food court ve 4. podlaží · ${esc(fcSt.label.toLowerCase())}</p></div><button class="btn btn--sm" type="button" id="pick">${icon('dice')} Vyber za mě</button></div>
      <div class="chips"><button class="chip" type="button" data-set="tag" data-val="" aria-pressed="${!tag}">Vše</button>${D.foodTags.map((t) => `<button class="chip" type="button" data-set="tag" data-val="${t.id}" aria-pressed="${tag === t.id}">${esc(t.label)}</button>`).join('')}</div>
      <div class="chips"><button class="chip chip--small" type="button" data-toggle="open" aria-pressed="${openOnly}">● Jen otevřené</button></div>
      <div id="pickBox"></div>
      <div class="list" style="margin-top:6px">${list.length ? list.map(shopRow).join('') : '<div class="empty">Teď nic neodpovídá filtru.</div>'}</div>
      <p class="tiny muted" style="margin-top:12px">McDonald’s má otevřeno do půlnoci, KFC do 22:30, Ginza do 22:30 a Bombay Express do 21:30 – i když ostatní obchody zavřely.</p>`;
  }

  function renderParking() {
    const P = D.parking, p = state.parking;
    let active = '';
    if (p) {
      const c = parkingCalc(p), pct = Math.min(100, (c.elapsed / c.free) * 100);
      active = `${c.elapsed > 18 * 60 ? `<section class="card card--warn notice" style="margin-bottom:12px">${icon('warn')}<div class="small"><b>Tohle hlídání běží od ${fmtDate(isoDate(c.arrival))}.</b> Pokud jste už odjeli, ukončete ho tlačítkem Odjíždím – částka níže není skutečná útrata.</div></section>` : ''}<section class="card card--wine" id="parkLive">
        <div class="row"><div class="grow small" style="opacity:.9">Zaparkováno od ${fmtClock(c.arrival)}${p.level ? ` · úroveň ${esc(p.level)}` : ''}${p.spot ? ` · ${esc(p.spot)}` : ''}</div><button class="iconbtn" type="button" data-editpark aria-label="Upravit">${icon('pin')}</button></div>
        <div class="big" style="margin-top:10px" id="parkElapsed">${dur(c.elapsed)}</div>
        <div class="progress" aria-hidden="true"><i style="width:${pct}%"></i></div>
        <div class="small" id="parkInfo">${c.cost ? `<b>Aktuálně ${c.cost} Kč</b> (${c.paidHours} ${c.paidHours === 1 ? 'započatá hodina' : c.paidHours < 5 ? 'započaté hodiny' : 'započatých hodin'}). Další hodina (+${P.rate} Kč) začne za ${dur(c.nextIn)}.` : `<b>Zatím zdarma.</b> Bezplatná doba končí v ${fmtClock(c.freeUntil)} (za ${dur(c.nextIn)}), pak ${P.rate} Kč za každou započatou hodinu.`}</div>
        <div class="row" style="margin-top:14px;gap:8px;flex-wrap:wrap"><label class="check small" style="min-height:36px"><input type="checkbox" id="bonus" ${p.bonus ? 'checked' : ''}> +3 h zdarma (kino, fitness, myčka)</label></div>
        <div class="row" style="margin-top:10px;gap:8px"><button class="btn btn--light grow" type="button" data-remind>${icon('clock')} Připomenout 10 min předem</button><button class="btn btn--danger" type="button" data-endpark>Odjíždím</button></div>
      </section>`;
    } else {
      const d = now();
      active = `<section class="card">
        <h2>Hlídač parkovného</h2>
        <p class="small muted" style="margin-top:4px">Zapište si, kdy a kde jste zaparkovali. Aplikace spočítá, dokdy je parkování zdarma a kolik zaplatíte.</p>
        <form id="parkForm" class="stack" style="margin-top:10px">
          <div class="fields">
            <label class="field">Čas příjezdu<input type="time" name="time" value="${fmtClock(d).padStart(5, '0')}" required></label>
            <label class="field">Úroveň garáže<select name="level"><option value="">nevím</option><option>−1</option><option>−2</option><option>−3</option><option>−4</option></select></label>
          </div>
          <label class="field">Kde stojím (volitelné)<input type="text" name="spot" placeholder="např. u výtahu B, řada 12, modrý sloup" maxlength="60"></label>
          <label class="check"><input type="checkbox" name="bonus"> Jdu do kina / fitness / na myčku (+3 h zdarma)</label>
          <button class="btn btn--block" type="submit">${icon('car')} Zaparkoval(a) jsem</button>
        </form>
      </section>`;
    }
    return `
      <div class="page-head"><div class="grow"><h1>Parkování</h1><p class="sub">Podzemní garáže, vjezd ${esc(P.entrance)} · ${esc(P.hours.split(' (')[0])}</p></div></div>
      ${active}
      <section class="card section">
        <h2>Kolik to stojí</h2>
        <dl class="kv" style="margin-top:10px">${P.rules.map((r) => `<dt>${esc(r.when)}</dt><dd>${r.free / 60} ${r.free === 60 ? 'hodina' : 'hodiny'} zdarma</dd>`).join('')}<dt>Každá další započatá hodina</dt><dd>${P.rate} Kč</dd><dt>Ztráta lístku</dt><dd>${P.lostTicket} Kč + parkovné</dd></dl>
        <p class="small" style="margin:12px 0 0">🎬 ${esc(P.bonusText)}</p>
        <p class="tiny muted" style="margin:8px 0 0">Bezplatná doba se počítá od času příjezdu na lístku. Platba: ${P.payment.map((x) => x.toLowerCase()).join(', ')}. Parkoviště je v provozu ${esc(P.hours)}.</p>
      </section>
      <section class="card section">
        <h2>${icon('bolt', 'ico')} Nabíjení elektromobilů</h2>
        <p class="small" style="margin-top:8px">${esc(P.ev.where)}.</p>
        <ul class="small" style="margin:0;padding-left:18px">${P.ev.stations.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>
        <p class="tiny muted" style="margin:8px 0 0">${esc(P.ev.operator)}. Každý stojan má dvě parkovací místa.</p>
      </section>
      <section class="card card--flat section small"><b>Noční a dlouhodobé stání.</b> ${esc(P.longterm.replace(/^Dlouhodobé a noční parkování /, ""))}.</section>
      <section class="section"><a class="btn btn--ghost btn--block" href="https://www.ocflora.cz/parkovani/" target="_blank" rel="noopener">${icon('external')} Parkovací řád a detaily na ocflora.cz</a></section>`;
  }

  function renderMap(_, q) {
    const sel = q.floor != null && q.floor !== '' ? Number(q.floor) : null;
    const counts = Object.fromEntries(D.floors.map((f) => [f.n, D.shops.filter((s) => s.floor === f.n).length]));
    const list = sel != null ? D.shops.filter((s) => s.floor === sel) : [];
    const f = D.floors.find((x) => x.n === sel);
    return `
      <div class="page-head"><div class="grow"><h1>Plán centra</h1><p class="sub">${D.center.address}</p></div></div>
      <div class="floors">${[...D.floors].reverse().map((fl) => `<a class="floorrow" href="#/mapa?floor=${fl.n}" ${sel === fl.n ? 'aria-current="true" style="outline:2px solid var(--wine)"' : ''}><span class="floor ${fl.n < 0 ? 'is-garage' : ''}">${fl.label}</span><div class="grow"><b>${esc(fl.name)}</b><div class="tiny muted">${esc(fl.desc)}</div></div><span class="badge">${counts[fl.n]}</span></a>`).join('')}</div>
      ${f ? `<section class="section"><div class="section__head"><h2>${f.label}. podlaží – ${esc(f.name)}</h2><a href="#/mapa">Zavřít</a></div><div class="list">${list.map(shopRow).join('') || '<div class="empty">V tomto podlaží neevidujeme žádné obchody.</div>'}</div></section>` : ''}
      <section class="card section">
        <h2>Interaktivní plán</h2>
        <p class="small muted" style="margin-top:4px">Plán od provozovatele centra (Simplaq) – po načtení můžete přibližovat a klepat na jednotky.</p>
        <div id="mapframe"></div>
        <button class="btn btn--block" type="button" data-showmap="" style="margin-top:10px">${icon('map')} Načíst interaktivní plán</button>
      </section>
      <section class="card card--flat section small"><b>Orientace:</b> hlavní vstup je z Vinohradské ulice do 1. podlaží (přízemí). Food court, kino a dětský koutek najdete ve 4. podlaží, fitness v 5. Garáže jsou pod centrem, výdejní boxy ve vestibulu v −1.</section>`;
  }

  function renderEvents(id) {
    if (id) { const n = D.news.find((x) => x.id === id); return n ? renderEventDetail(n) : '<div class="empty">Aktualita nenalezena.</div>'; }
    const items = [...D.news].sort((a, b) => (b.start || b.date).localeCompare(a.start || a.date));
    const live = items.filter((n) => eventState(n) === 'live'), up = items.filter((n) => eventState(n) === 'upcoming'), past = items.filter((n) => ['past', 'info'].includes(eventState(n)));
    const block = (title, arr) => (arr.length ? `<section class="section"><h2 style="margin-bottom:10px">${title}</h2><div class="stack">${arr.map(eventCard).join('')}</div></section>` : '');
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><h1>Akce a novinky</h1></div></div>
      ${block('Právě probíhá', live)}${block('Chystáme', up)}${block('Proběhlo a archiv', past)}`;
  }
  function renderEventDetail(n) {
    const st = eventState(n);
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><p class="sub">${st === 'live' ? 'Právě probíhá' : st === 'upcoming' ? 'Chystá se' : 'Aktualita'} · ${fmtDate(n.date)}</p></div></div>
      <section class="card">
        <img class="event__img" src="${esc(n.image)}" alt="" style="margin:0 0 12px;aspect-ratio:16/5">
        <h1 style="font-size:1.3rem">${esc(n.title)}</h1>
        ${n.start ? `<div class="row row--wrap small" style="margin-top:8px"><span class="badge badge--wine">${n.end && n.end !== n.start ? `${fmtDate(n.start)} – ${fmtDate(n.end)}` : fmtDate(n.start)}</span>${n.time ? `<span class="badge">${esc(n.time)}</span>` : ''}${n.place ? `<span class="badge">${esc(n.place)}</span>` : ''}</div>` : ''}
        <p class="desc" style="margin-top:12px">${esc(n.text)}</p>
        <a class="btn btn--ghost btn--block" href="${esc(n.url)}" target="_blank" rel="noopener">${icon('external')} Celý článek na ocflora.cz</a>
      </section>`;
  }

  function renderOffers() {
    const offers = activeOffers();
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><h1>Aktuální nabídky</h1><p class="sub">${offers.length} akcí a novinek v prodejnách</p></div></div>
      <div class="grid">${offers.map((o) => offerCard(o, true)).join('') || '<div class="empty">Zrovna žádné nabídky.</div>'}</div>`;
  }
  function renderOffer(id) {
    const o = D.offers.find((x) => x.id === id);
    if (!o) return `<div class="empty">Nabídka nenalezena.</div>`;
    const shop = o.shopId ? byId[o.shopId] : null;
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><p class="sub">${esc(o.shop || 'OC Flora')}</p></div></div>
      <section class="card">
        <img class="offer__img" src="${esc(o.image)}" alt="" style="border-radius:12px;margin-bottom:12px">
        <h1 style="font-size:1.3rem">${esc(o.title)}</h1>
        <div class="row row--wrap" style="margin-top:8px"><span class="badge badge--gold">${esc(offerValidity(o))}</span>${o.from && o.to ? `<span class="tiny muted">${fmtDate(o.from)} – ${fmtDate(o.to)}</span>` : ''}</div>
        <p class="desc" style="margin-top:12px">${esc(o.text)}</p>
        ${shop ? shopRow(shop) : ''}
        <a class="btn btn--ghost btn--block" style="margin-top:12px" href="${esc(o.url)}" target="_blank" rel="noopener">${icon('external')} Detail na ocflora.cz</a>
      </section>`;
  }

  function renderMore() {
    const items = [
      ['info', 'clock', 'Otevírací doba a kontakt'], ['doprava', 'tram', 'Jak se k nám dostat'], ['mapa', 'map', 'Plán centra a patra'],
      ['karta', 'gift', 'Dárková karta OC Flora'], ['kino', 'film', 'Cinema City IMAX'], ['akce', 'info', 'Akce a novinky'], ['nabidky', 'bag', 'Nabídky prodejen'],
      ['oblibene', 'star', `Oblíbené (${state.favs.length})`], ['seznam', 'list', `Nákupní seznam (${state.list.filter((i) => !i.done).length})`],
    ];
    return `<div class="page-head"><div class="grow"><h1>Více</h1></div></div>
      <div class="linklist">${items.map(([r, i, l]) => `<a href="#/${r}">${icon(i)}<span class="grow">${l}</span>${icon('chev', 'chev')}</a>`).join('')}</div>
      <section class="card section">
        <h2>Nastavení</h2>
        <div class="row" style="margin-top:10px;justify-content:space-between"><span class="small">Vzhled</span><div class="seg" role="group" aria-label="Vzhled">${['auto', 'light', 'dark'].map((t) => `<button type="button" data-theme="${t}" aria-pressed="${state.theme === t}">${{ auto: 'Auto', light: 'Světlý', dark: 'Tmavý' }[t]}</button>`).join('')}</div></div>
        <div class="row" style="margin-top:12px;justify-content:space-between"><span class="small">Spořič obrazovky (video pro infopanely)</span><button class="btn btn--sm btn--light" type="button" id="saverBtn">${icon('film')} Přehrát</button></div>
        <div id="installRow" class="row hidden" style="margin-top:12px;justify-content:space-between"><span class="small">Přidat aplikaci na plochu</span><button class="btn btn--sm" type="button" id="installBtn">Nainstalovat</button></div>
        ${isSim() ? `<div class="row" style="margin-top:12px;justify-content:space-between"><span class="small">Simulovaný čas: <b>${fmtClock(now())}, ${fmtDate(todayIso())}</b></span><button class="btn btn--sm btn--light" type="button" id="resetTime">Zrušit</button></div>` : ''}
      </section>
      <section class="card card--flat section small">
        <b>O aplikaci.</b> Neoficiální prototyp průvodce pro zákazníky OC Flora. Data (obchody, hodiny, nabídky, akce) pocházejí z veřejného webu ocflora.cz, stav k ${fmtDate(D.meta.updated)}. Vaše oblíbené, parkování a seznam zůstávají jen ve vašem zařízení.
        <div style="margin-top:8px"><a href="https://www.ocflora.cz/" target="_blank" rel="noopener">ocflora.cz</a> · <a href="https://www.ocflora.cz/navstevni-rad/" target="_blank" rel="noopener">Návštěvní řád</a> · <a href="https://www.ocflora.cz/kariera/" target="_blank" rel="noopener">Kariéra</a></div>
      </section>`;
  }

  function renderInfo() {
    const wi = weekIdx(now());
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><h1>Otevírací doba a kontakt</h1></div></div>
      <section class="card">
        <table class="hours">${D.center.hours.map((h) => { const st = status(h.week); return `<tr><td><b>${esc(h.label)}</b><div class="tiny"><span class="status status--${st.cls}">${esc(st.label)}</span></div></td><td>${hoursText(h.week[wi])}<div class="tiny muted">${h.week.every((x) => JSON.stringify(x) === JSON.stringify(h.week[0])) ? 'denně' : `dnes (${DAYS_LONG[now().getDay()]})`}</div></td></tr>`; }).join('')}</table>
        <p class="tiny muted" style="margin:10px 0 0">Obchody: Po–So 9:00–21:00, Ne 10:00–21:00. Jednotlivé prodejny mohou mít hodiny odlišné – najdete je v detailu obchodu.</p>
      </section>
      <section class="card section">
        <h2>Kontakt</h2>
        <dl class="kv" style="margin-top:10px"><dt>Adresa</dt><dd style="text-align:right">${esc(D.center.address)}</dd><dt>Recepce</dt><dd><a href="tel:${D.center.phone.replace(/\s/g, '')}">${D.center.phone}</a></dd><dt>E-mail</dt><dd><a href="mailto:${D.center.email}">${D.center.email}</a></dd><dt>Správa centra</dt><dd>${esc(D.center.reception)}</dd></dl>
        <div class="row" style="margin-top:12px;gap:8px"><a class="btn btn--light grow" href="https://maps.google.com/?q=${D.center.gps.join(',')}" target="_blank" rel="noopener">${icon('pin')} Navigovat</a><a class="btn btn--light grow" href="tel:${D.center.phone.replace(/\s/g, '')}">${icon('phone')} Zavolat</a></div>
        <p class="tiny muted" style="margin:10px 0 0">Ztráty a nálezy, reklamace dárkových karet a dotazy k parkování řeší Správa centra v pracovní době.</p>
      </section>
      <section class="card card--tint section small"><b>Zajímavosti:</b> ${D.center.facts.join(' · ')}.</section>`;
  }

  function renderTransport() {
    const T = D.transport;
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><h1>Jak se k nám dostat</h1></div></div>
      <section class="card card--warn notice">${icon('warn')}<div><b>Metro Flora je uzavřené</b> od ${fmtDate(T.metroClosed.from)}.<br><span class="small">${esc(T.metroClosed.text)}</span></div></section>
      <section class="card section">
        <h2>${icon('tram', 'ico')} Tramvají a autobusem</h2>
        <p class="small" style="margin-top:8px">Zastávka <b>${esc(T.stop)}</b>.</p>
        <div class="row row--wrap">${T.trams.map((l) => `<span class="badge badge--wine" style="font-size:1rem;padding:6px 12px">${l}</span>`).join('')}</div>
        <p class="tiny muted" style="margin:10px 0 0">Linky podle výlukových informací PID k ${fmtDate(D.meta.updated)}. Aktuální odjezdy: <a href="https://pid.cz" target="_blank" rel="noopener">pid.cz</a>, infolinka ${T.pid}.</p>
      </section>
      <section class="card section">
        <h2>Metrem (linka A) – nejbližší stanice</h2>
        <dl class="kv" style="margin-top:10px">${T.alt.map((a) => `<dt>${esc(a.from)}</dt><dd style="text-align:right;font-weight:500">${esc(a.how)}</dd>`).join('')}</dl>
      </section>
      <section class="card section">
        <h2>${icon('car', 'ico')} Autem</h2>
        <p class="small" style="margin-top:8px">Podzemní garáže s více než 500 místy, vjezd ${esc(D.parking.entrance)}. První hodina ve všední den zdarma, večer a o víkendu 3 hodiny. <a href="#/parkovani">Detaily a hlídač parkovného</a>.</p>
        <a class="btn btn--light btn--block" href="https://maps.google.com/?q=${D.center.gps.join(',')}" target="_blank" rel="noopener">${icon('pin')} Navigovat do garáží (Jičínská)</a>
      </section>`;
  }

  function renderGift() {
    const G = D.giftcard, accepting = D.shops.filter((s) => s.gift).length;
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><h1>Dárková karta</h1></div></div>
      <section class="card card--wine"><div class="row">${icon('gift')}<div class="grow"><b>Jedna karta, ${accepting} prodejen.</b><div class="small" style="opacity:.9">Hodnota ${G.range[0]}–${G.range[1].toLocaleString('cs')} Kč, platnost ${esc(G.validity)}.</div></div></div></section>
      <section class="card section">
        <dl class="kv"><dt>Kde koupit</dt><dd style="text-align:right;font-weight:500">${esc(G.where)}</dd><dt>Platba za kartu</dt><dd style="text-align:right;font-weight:500">${esc(G.payment)}</dd><dt>Jak platit</dt><dd style="text-align:right;font-weight:500">${esc(G.how)}</dd><dt>V mobilu</dt><dd style="text-align:right;font-weight:500">${esc(G.wallet)}</dd><dt>Ztráta / poškození</dt><dd style="text-align:right;font-weight:500">${esc(G.replace)}</dd></dl>
        <a class="btn btn--block" style="margin-top:14px" href="${G.balance}" target="_blank" rel="noopener">${icon('external')} Zkontrolovat zůstatek</a>
      </section>
      <section class="section"><div class="section__head"><h2>Kde kartu uplatníte</h2><a href="#/obchody?gift=1">Celý seznam</a></div><p class="small muted">Téměř všechny obchody přijímající platební karty – včetně Albertu, dm, H&M, Sephory a restaurací ve food courtu. Kartu nepřijímají banky, směnárna, výdejní boxy a některé služby.</p></section>
      <section class="card card--flat section small">Hromadné objednávky pro firmy: <a href="mailto:${D.center.email}">${D.center.email}</a>. Podrobné podmínky na <a href="https://www.ocflora.cz/darkove-karty/" target="_blank" rel="noopener">ocflora.cz</a>.</section>`;
  }

  function renderCinema() {
    const s = byId['cinema-city'], st = status(s.hours);
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><h1>Cinema City Flora</h1><p class="sub">4. podlaží · <span class="status status--${st.cls}">${esc(st.label)}</span></p></div></div>
      <section class="card">
        <p>8 klimatizovaných sálů a jediné <b>3D kino IMAX</b> v České republice. Pokladny otevírají Po–Pá od 14:00, So–Ne od 11:00.</p>
        <div class="row" style="gap:8px;flex-wrap:wrap"><a class="btn grow" href="https://www.cinemacity.cz/cinemas/flora/1010" target="_blank" rel="noopener">${icon('film')} Program a vstupenky</a><a class="btn btn--light grow" href="#/obchod/cinema-city">Detail a kontakt</a></div>
      </section>
      <section class="card card--ok section notice">${icon('car')}<div class="small"><b>Parkování zdarma na 3 hodiny navíc.</b> Parkovací lístek si nechte označit u pokladny kina. Po posledním představení můžete z garáží odjet i po půlnoci.</div></section>
      <section class="card card--flat section small">Před filmem: food court je hned vedle (4. podlaží), McDonald’s má otevřeno do 24:00, KFC a Ginza do 22:30.</section>`;
  }

  function renderFavs() {
    const favs = state.favs.map((id) => byId[id]).filter(Boolean);
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><h1>Oblíbené</h1></div></div>
      <div class="list">${favs.length ? favs.map(shopRow).join('') : `<div class="empty">Zatím nemáte oblíbené obchody.<br><a class="btn" style="margin-top:12px" href="#/obchody">Procházet obchody</a></div>`}</div>`;
  }

  function renderList() {
    const items = state.list;
    return `<div class="page-head"><button class="iconbtn iconbtn--ink" type="button" data-back aria-label="Zpět">${icon('back')}</button><div class="grow"><h1>Nákupní seznam</h1></div>${items.some((i) => i.done) ? `<button class="btn btn--sm btn--light" type="button" data-clear-done>Smazat hotové</button>` : ''}</div>
      <form id="listForm" class="search" style="margin-bottom:12px">${icon('plus')}<input name="text" type="text" placeholder="Přidat položku (např. Albert – mléko)" maxlength="80" autocomplete="off" aria-label="Nová položka"><button class="btn btn--sm" type="submit">Přidat</button></form>
      <div class="stack">${items.length ? items.map((it, i) => `<label class="todo ${it.done ? 'is-done' : ''}"><input type="checkbox" data-done="${i}" ${it.done ? 'checked' : ''}><span class="todo__text">${esc(it.text)}</span><button class="iconbtn iconbtn--ink" style="width:36px;height:36px" type="button" data-del="${i}" aria-label="Smazat">${icon('x')}</button></label>`).join('') : '<div class="empty">Seznam je prázdný. Přidejte, co chcete nakoupit – nebo v detailu obchodu klepněte na „Do seznamu“.</div>'}</div>`;
  }

  /* ---------- Chování po vykreslení ---------- */
  function afterRender(route) {
    if (route === 'obchody') {
      renderShopList();
      const q = $('#q');
      q.addEventListener('input', () => { setQuery({ q: q.value }); $('#qClear').classList.toggle('hidden', !q.value); renderShopList(); });
      $('#qClear').addEventListener('click', () => { q.value = ''; setQuery({ q: '' }); $('#qClear').classList.add('hidden'); renderShopList(); q.focus(); });
      if (currentQuery.focus) q.focus();
    }
    if (route === 'parkovani' && state.parking) {
      render.tick = setInterval(() => {
        const c = parkingCalc(state.parking); const el = $('#parkElapsed'); if (!el) return;
        el.textContent = dur(c.elapsed);
        $('#parkInfo').innerHTML = c.cost ? `<b>Aktuálně ${c.cost} Kč</b>. Další hodina (+${D.parking.rate} Kč) začne za ${dur(c.nextIn)}.` : `<b>Zatím zdarma.</b> Bezplatná doba končí v ${fmtClock(c.freeUntil)} (za ${dur(c.nextIn)}).`;
        $('.progress i').style.width = Math.min(100, (c.elapsed / c.free) * 100) + '%';
      }, 15000);
    }
    if (route === 'vice') {
      if (deferredInstall) $('#installRow').classList.remove('hidden');
      $('#saverBtn')?.addEventListener('click', () => window.FloraSaver && window.FloraSaver.show(true));
      $('#installBtn')?.addEventListener('click', async () => { deferredInstall.prompt(); await deferredInstall.userChoice; deferredInstall = null; $('#installRow').classList.add('hidden'); });
      $('#resetTime')?.addEventListener('click', () => { sessionStorage.removeItem('flora-now'); location.href = location.pathname + '#/vice'; location.reload(); });
    }
    renderTopStatus();
  }

  /* ---------- Události (delegace) ---------- */
  view.addEventListener('click', (e) => {
    const t = e.target.closest('[data-back],[data-set],[data-toggle],[data-fav],[data-showmap],[data-addlist],[data-dismiss],[data-endpark],[data-editpark],[data-remind],[data-theme],[data-del],[data-clear-done]');
    if (!t) return;
    if (t.hasAttribute('data-back')) { e.preventDefault(); history.length > 1 ? history.back() : (location.hash = '#/dnes'); return; }
    if (t.dataset.set !== undefined) { setQuery({ [t.dataset.set]: t.dataset.val }); render.keepScroll = true; render(); return; }
    if (t.dataset.toggle) { setQuery({ [t.dataset.toggle]: currentQuery[t.dataset.toggle] === '1' ? '' : '1' }); render.keepScroll = true; render(); return; }
    if (t.dataset.fav) {
      const id = t.dataset.fav, i = state.favs.indexOf(id);
      i >= 0 ? state.favs.splice(i, 1) : state.favs.push(id); save();
      toast(i >= 0 ? 'Odebráno z oblíbených' : 'Přidáno do oblíbených'); render.keepScroll = true; render(); return;
    }
    if (t.dataset.showmap !== undefined) {
      const box = $('#mapframe'); if (!box) return;
      const ent = t.dataset.showmap;
      box.innerHTML = `<iframe class="mapframe" title="Interaktivní plán OC Flora" loading="lazy" src="https://atriumflora.mysimplaq.com/assets/mall?floorplanID=1&hideUi=true${ent ? '&entityId=' + encodeURIComponent(ent) : ''}"></iframe>`;
      $('#mapbox')?.classList.remove('hidden'); t.classList.add('hidden'); box.scrollIntoView({ behavior: 'smooth', block: 'center' }); return;
    }
    if (t.dataset.addlist) { state.list.unshift({ text: t.dataset.addlist, done: false }); save(); toast(`„${t.dataset.addlist}“ přidáno do nákupního seznamu`); return; }
    if (t.dataset.dismiss) { state.dismissed.push(t.dataset.dismiss); save(); render(); return; }
    if (t.hasAttribute('data-endpark')) {
      const c = parkingCalc(state.parking);
      if (confirm(`Ukončit hlídání parkování?\nCelkem ${dur(c.elapsed)}, odhad ${c.cost} Kč.`)) { state.parking = null; save(); clearTimeout(remindTimer); render(); toast('Šťastnou cestu!'); }
      return;
    }
    if (t.hasAttribute('data-editpark')) {
      const p = state.parking, lvl = prompt('Úroveň garáže (např. −2):', p.level || ''); if (lvl === null) return;
      const spot = prompt('Kde stojíte (sloup, řada, výtah):', p.spot || ''); if (spot === null) return;
      p.level = lvl.trim(); p.spot = spot.trim(); save(); render(); return;
    }
    if (t.hasAttribute('data-remind')) { scheduleReminder(); return; }
    if (t.dataset.theme) { state.theme = t.dataset.theme; save(); if (state.theme === 'auto') delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = state.theme; render.keepScroll = true; render(); return; }
    if (t.dataset.del !== undefined) { state.list.splice(Number(t.dataset.del), 1); save(); render.keepScroll = true; render(); return; }
    if (t.hasAttribute('data-clear-done')) { state.list = state.list.filter((i) => !i.done); save(); render(); return; }
  });
  view.addEventListener('change', (e) => {
    if (e.target.id === 'bonus' && state.parking) { state.parking.bonus = e.target.checked; save(); render.keepScroll = true; render(); }
    if (e.target.dataset.done !== undefined) { state.list[Number(e.target.dataset.done)].done = e.target.checked; save(); render.keepScroll = true; render(); }
  });
  view.addEventListener('submit', (e) => {
    if (e.target.id === 'parkForm') {
      e.preventDefault();
      const f = new FormData(e.target), [h, m] = String(f.get('time')).split(':').map(Number);
      const d = now(); d.setHours(h, m, 0, 0);
      if (d > now()) d.setDate(d.getDate() - 1); // příjezd včera večer
      state.parking = { arrivedAt: d.toISOString(), level: f.get('level') || '', spot: String(f.get('spot') || '').trim(), bonus: f.get('bonus') === 'on' };
      save(); render(); toast('Hlídám parkovné');
    }
    if (e.target.id === 'listForm') {
      e.preventDefault(); const text = String(new FormData(e.target).get('text') || '').trim(); if (!text) return;
      state.list.unshift({ text, done: false }); save(); render(); $('#listForm input')?.focus();
    }
  });
  $('#btnSearch').addEventListener('click', () => { location.hash = '#/obchody?focus=1'; });
  view.addEventListener('click', (e) => {
    if (e.target.closest('#pick')) {
      const open = D.shops.filter((s) => s.cat === 'jidlo' && status(s.hours).open && (!currentQuery.tag || s.tags.includes(currentQuery.tag)));
      const pool = open.length ? open : D.shops.filter((s) => s.cat === 'jidlo');
      const s = pool[Math.floor(Math.random() * pool.length)];
      $('#pickBox').innerHTML = `<div class="card card--tint" style="margin:6px 0 10px"><div class="tiny muted">Náš tip${open.length ? '' : ' (teď je zavřeno, ale zítra…)'}:</div>${shopRow(s)}</div>`;
    }
  });

  /* ---------- Připomínka parkování (jen při otevřené aplikaci / povolených notifikacích) ---------- */
  let remindTimer;
  async function scheduleReminder() {
    if (!state.parking) return;
    const c = parkingCalc(state.parking), ms = (c.nextIn - 10) * 60000;
    if (ms <= 0) { toast('Do konce bezplatné doby zbývá méně než 10 minut.'); return; }
    let granted = false;
    if ('Notification' in window) { if (Notification.permission === 'granted') granted = true; else if (Notification.permission !== 'denied') granted = (await Notification.requestPermission()) === 'granted'; }
    clearTimeout(remindTimer);
    remindTimer = setTimeout(() => {
      const msg = `Za 10 minut končí ${c.cost ? 'započatá hodina' : 'bezplatné parkování'} v OC Flora.`;
      if (granted) new Notification('OC Flora – parkování', { body: msg, icon: 'assets/icon-192.png' }); toast(msg);
    }, ms);
    toast(`Připomenu v ${fmtClock(new Date(now().getTime() + ms))}${granted ? '' : ' (jen pokud bude aplikace otevřená)'}`);
  }

  /* ---------- PWA ---------- */
  let deferredInstall = null;
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferredInstall = e; $('#installRow')?.classList.remove('hidden'); });
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js').catch(() => {});

  render();
  setInterval(renderTopStatus, 60000);
})();
