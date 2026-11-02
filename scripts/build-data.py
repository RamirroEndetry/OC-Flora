# -*- coding: utf-8 -*-
"""Build data.js for the OC Flóra app from data/raw-ocflora.json (output of scrape-ocflora.py).
Usage: python -X utf8 scripts/build-data.py data/raw-ocflora.json data.js
"""
import json, re, sys, datetime, unicodedata

RAW, OUT = sys.argv[1], sys.argv[2]
raw = json.load(open(RAW, encoding='utf-8'))

DAYS = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']
CATS = {
    'Móda': 'moda', 'Obuv': 'obuv', 'Zdraví, Krása': 'krasa', 'Šperky, Hodinky': 'sperky',
    'Interiér, Elektronika, Hudba': 'elektro', 'Knihy, Dárky, Hračky': 'darky',
    'Potraviny, Lahůdky': 'potraviny', 'Restaurace, Občerstvení': 'jidlo', 'Služby': 'sluzby', 'Zábava': 'zabava',
}
CAT_LABELS = {
    'moda': 'Móda', 'obuv': 'Obuv', 'krasa': 'Zdraví a krása', 'sperky': 'Šperky a hodinky',
    'elektro': 'Domácnost a elektro', 'darky': 'Knihy, dárky, hračky', 'potraviny': 'Potraviny a lahůdky',
    'jidlo': 'Restaurace a kavárny', 'sluzby': 'Služby', 'zabava': 'Zábava',
}
# Ruční štítky (kuchyně / typ služby) pro rychlé filtry v aplikaci.
TAGS = {
    'costa-coffee': ['kava'], 'starbucks': ['kava'], 'df-cafe': ['kava', 'asie'], 'tchibo': ['kava'], 'oxalis-cajkava': ['kava', 'caj'],
    'pearly-tea': ['caj', 'sladke'], 'paul-stanek': ['kava', 'pecivo', 'sladke'], 'minit-bakery': ['pecivo', 'sladke'],
    'armins-cake': ['sladke'], 'ovocny-svetozor': ['sladke'], 'lindt': ['sladke'], 'fruitisimo-fresh-bar': ['zdrave', 'sladke'],
    'pai-thai': ['asie'], 'wok-dej': ['asie'], 'ginza-running-sushi': ['asie', 'sushi'], 'pholevka': ['asie', 'polevka'],
    'bombay-express': ['asie', 'indie'], 'poke-fun': ['asie', 'zdrave'], 'kfc': ['fastfood'], 'mcdonalds': ['fastfood'],
    'bageterie-boulevard': ['fastfood', 'pecivo'], 'ugo-salaterie': ['zdrave', 'polevka'], 'loving-bistro': ['zdrave', 'vege'],
    'prima-basta': ['ceska'], 'ifood': ['fastfood'], 'vilgain': ['zdrave'], 'grizly': ['zdrave'],
    # služby
    'alzabox-garaz': ['box'], 'alzabox-vestibul': ['box'], 'z-box-zasilkovna': ['box'], 'dhl-locker': ['box'], 'benu-vydejni-box': ['box'],
    'benu-lekarna': ['lekarna'], 'dr-max-lekarna': ['lekarna'], 'mbank': ['banka'], 'unicredit-bank': ['banka'], 'smenarna': ['banka'],
    'kadernictvi-no-1': ['pece'], 'fastcut-barbershop': ['pece'], 'euronails': ['pece'], 'beauty-center': ['pece'],
    'rychloopravna-obuvi-a-vyroba-klicu': ['opravy'], 'upravy-odevu': ['opravy'], 'iloveservis': ['opravy'], 'cleany-cz': ['opravy'],
    'automycka-express': ['auto'], 'pneu-hulin': ['auto'], 'snowlab-2': ['sport'], 'max-fitness': ['sport'],
    'o2': ['operator'], 't-mobile': ['operator'], 'vodafone': ['operator'], 'detsky-koutek': ['deti'],
    'mycopy-1-patro': ['tisk'], 'mycopy-4-patro': ['tisk'], 'dobijmat': ['nabijeni'],
    'fresh-flowers': ['kvetiny'], 'holandske-kvetiny': ['kvetiny'], 'ck-fischer': ['cestovani'], 'invia': ['cestovani'],
    'grandoptical': ['optika'], 'kodano-optik': ['optika'], 'fortuna': ['sazky'], 'tabak-valmont': ['tisk'],
}


import os
def logo_path(slug):
    for ext in ('png', 'svg'):
        if os.path.exists('assets/logos/%s.%s' % (slug, ext)):
            return 'assets/logos/%s.%s' % (slug, ext)
    return ''


LIGHT_LOGOS = {'fastcut-barbershop'}  # loga kreslená jen bílou – zobrazit na tmavém podkladu


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def t2m(t):
    h, m = t.split(':')
    return int(h) * 60 + int(m)


def parse_hours(rows):
    """[['Po–So','9:00–21:00'],['Ne','10:00–21:00']] -> 7x [open,close] v minutách nebo None"""
    week = [None] * 7
    for days, times in rows:
        days = days.replace('-', '–').strip()
        times = times.replace('-', '–').replace(' ', '')
        tm = re.match(r'(\d{1,2}:\d{2})–(\d{1,2}:\d{2})', times)
        if not tm:
            continue
        span = [t2m(tm.group(1)), t2m(tm.group(2))]
        if '–' in days:
            a, b = [DAYS.index(x.strip()) for x in days.split('–')]
            idx = range(a, b + 1)
        else:
            idx = [DAYS.index(days)]
        for i in idx:
            week[i] = span
    return week


def parse_floor(f):
    if not f:
        return None
    m = re.match(r'(-?\d+)', f.strip())
    return int(m.group(1)) if m else None


def tidy(text):
    text = text.replace(' ', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


shops = []
for s in raw['shops']:
    cat = CATS.get(s.get('category'), 'sluzby')
    shops.append({
        'id': s['slug'], 'name': s['name'].replace('`', '’'), 'cat': cat, 'floor': parse_floor(s.get('floor')),
        'hours': parse_hours(s.get('hours') or []), 'gift': (s.get('giftcard') == 'Ano'),
        'phone': s.get('phone') or '', 'web': s.get('web') or '', 'email': s.get('email') or '',
        'logo': logo_path(s['slug']), 'desc': tidy(s.get('desc') or ''), 'url': s['url'],
        'entity': s.get('entityId'), 'tags': TAGS.get(s['slug'], []), 'logoDark': s['slug'] in LIGHT_LOGOS,
        'q': strip_accents(s['name'] + ' ' + (s.get('desc') or '')[:300] + ' ' + ' '.join(TAGS.get(s['slug'], []))),
    })
shops.sort(key=lambda x: strip_accents(x['name']))


def cz_date(d):
    m = re.match(r'(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})', d.strip())
    return '%s-%02d-%02d' % (m.group(3), int(m.group(2)), int(m.group(1))) if m else None


name2id = {s['name'].upper(): s['id'] for s in shops}
offers = []
for o in raw['offers']:
    body = re.sub(r'^.*?\n', '', o['body'], count=1)
    shop = re.search(r'Tuto nabídku nabízí:\s*(.+?)\s*$', body, re.S)
    val = re.search(r'Tato nabídka platí:\s*([^\n]+)', body)
    text = re.split(r'Tato nabídka platí:|Tuto nabídku nabízí:', body)[0]
    text = tidy(re.sub(r'^\s*' + re.escape(o['title']) + r'\s*', '', text.strip()))
    vf = vt = None
    if val:
        ds = re.findall(r'\d{1,2}\.\s*\d{1,2}\.\s*\d{4}', val.group(1))
        if len(ds) >= 1:
            vf = cz_date(ds[0])
        if len(ds) >= 2:
            vt = cz_date(ds[1])
    pub = cz_date(o['date']) or ''
    if pub < '2026-09-01':
        continue  # starší nabídky už neukazujeme
    shop_name = shop.group(1).strip() if shop else ''
    offers.append({'id': o['slug'], 'title': o['title'], 'shop': shop_name, 'shopId': name2id.get(shop_name.upper()),
                   'date': pub, 'from': vf, 'to': vt, 'image': o['image'], 'text': text[:600], 'url': o['url']})
offers.sort(key=lambda x: (x['to'] or '9999', x['date']), reverse=True)

# Aktuality + akce – ručně doplněné termíny konání (z textu článků)
EVENTS = {
    'zahrejte-se-vyhrou': {'start': '2026-11-02', 'end': '2026-11-06', 'time': '14:00–19:00', 'place': '2. podlaží, pasáž', 'kind': 'soutez'},
    'army-den-na-flore': {'start': '2026-10-10', 'end': '2026-10-10', 'time': '10:00–18:00', 'place': 'pasáž a okolí centra', 'kind': 'akce'},
    'zveme-vas-na-medobrani-v-oc-flora': {'start': '2026-06-29', 'end': '2026-06-29', 'time': '15:00–17:00', 'place': 'pasáž', 'kind': 'akce'},
    'straznici-na-flore': {'start': '2026-05-16', 'end': '2026-05-16', 'time': '10:00–18:00', 'place': 'pasáž a okolí centra', 'kind': 'akce'},
    'uz-12-srpna-otevira-v-oc-flora-prvni-prodejna-normal-v-ceske-republice': {'start': '2026-08-12', 'end': '2026-08-12', 'time': '8:00', 'place': '3. podlaží', 'kind': 'novinka'},
    'nakupte-darkovou-kartu-a-odneste-si-darek': {'start': None, 'end': None, 'time': '', 'place': 'Správa centra', 'kind': 'info'},
    'metro-flora-bude-docasne-uzavreno-oc-flora-zustava-otevrene': {'start': '2026-02-02', 'end': '2027-02-28', 'time': '', 'place': 'stanice metra Flora', 'kind': 'doprava'},
}
news = []
for n in raw['news']:
    body = re.sub(r'^.*?\n', '', n['body'], count=1)
    body = tidy(re.sub(r'^\s*' + re.escape(n['title']) + r'\s*', '', body.strip()))
    ev = EVENTS.get(n['slug'], {})
    item = {'id': n['slug'], 'title': n['title'], 'date': cz_date(n['date']), 'image': n['image'], 'text': body[:1800], 'url': n['url']}
    item.update(ev)
    news.append(item)
news.sort(key=lambda x: x['date'], reverse=True)

data = {
    'meta': {'updated': datetime.date.today().isoformat(), 'source': 'https://www.ocflora.cz/', 'shopCount': len(shops)},
    'center': {
        'name': 'OC Flora', 'address': 'Vinohradská 2828/151, 130 00 Praha 3 – Vinohrady', 'gps': [50.0781, 14.4617],
        'phone': '+420 255 741 704', 'email': 'flora.recepce@redstonegroup.cz',
        'reception': 'Po–Čt 9:00–17:00, Pá 9:00–16:00 (Správa centra)',
        'hours': [
            {'id': 'galerie', 'label': 'Pasáž (galerie)', 'week': parse_hours([['Po–Ne', '7:00–24:00']])},
            {'id': 'obchody', 'label': 'Obchody', 'week': parse_hours([['Po–So', '9:00–21:00'], ['Ne', '10:00–21:00']])},
            {'id': 'foodcourt', 'label': 'Food court', 'week': parse_hours([['Po–Ne', '8:00–24:00']])},
            {'id': 'albert', 'label': 'Supermarket Albert', 'week': parse_hours([['Po–Ne', '7:00–24:00']])},
            {'id': 'kino', 'label': 'Cinema City', 'week': parse_hours([['Po–Pá', '14:00–22:00'], ['So–Ne', '11:00–22:00']])},
            {'id': 'fitness', 'label': 'Max Fitness', 'week': parse_hours([['Po–So', '6:00–22:00'], ['Ne', '7:00–22:00']])},
        ],
        'facts': ['Vítěz soutěže OC roku 2025', 'Jediné 3D IMAX kino v ČR', 'Více než 500 parkovacích míst', 'Vlastní včely na střeše od roku 2017 (6 úlů)'],
    },
    'floors': [
        {'n': -2, 'label': '−2', 'name': 'Garáže', 'desc': 'Parkování, Automyčka Express, lyžařský servis Snowlab'},
        {'n': -1, 'label': '−1', 'name': 'Garáže a vestibul', 'desc': 'Parkování, výdejní boxy (AlzaBox, Z-BOX, DHL, BENU), Pneu Hulín, nabíjení elektromobilů'},
        {'n': 1, 'label': '1', 'name': 'Přízemí', 'desc': 'Vstup z Vinohradské, supermarket Albert, drogerie, lékárna, lahůdky, květiny, služby'},
        {'n': 2, 'label': '2', 'name': 'Móda a krása', 'desc': 'H&M, Sephora, Rituals, obuv, šperky, banky, automat na dárkové karty'},
        {'n': 3, 'label': '3', 'name': 'Móda a dárky', 'desc': 'Intersport, Lindex, NORMAL, Luxor, Albi, Flying Tiger, Starbucks, operátoři'},
        {'n': 4, 'label': '4', 'name': 'Food court a kino', 'desc': 'Restaurace a rychlé občerstvení, Cinema City IMAX, dětský koutek'},
        {'n': 5, 'label': '5', 'name': 'Fitness', 'desc': 'Max Fitness (2 500 m²)'},
    ],
    'cats': [{'id': k, 'label': v} for k, v in CAT_LABELS.items()],
    'foodTags': [
        {'id': 'kava', 'label': '☕ Káva'}, {'id': 'sladke', 'label': '🍰 Sladké'}, {'id': 'asie', 'label': '🍜 Asie'},
        {'id': 'fastfood', 'label': '🍔 Fast food'}, {'id': 'zdrave', 'label': '🥗 Zdravě'}, {'id': 'ceska', 'label': '🍖 Česká'},
        {'id': 'pecivo', 'label': '🥐 Pečivo'}, {'id': 'polevka', 'label': '🍲 Polévky'},
    ],
    'serviceTags': [
        {'id': 'box', 'label': '📦 Výdejní boxy'}, {'id': 'lekarna', 'label': '💊 Lékárny'}, {'id': 'banka', 'label': '🏦 Banky a směnárna'},
        {'id': 'pece', 'label': '💇 Kadeřník, nehty'}, {'id': 'opravy', 'label': '🔧 Opravy, čistírna'}, {'id': 'auto', 'label': '🚗 Auto'},
        {'id': 'operator', 'label': '📱 Operátoři'}, {'id': 'optika', 'label': '👓 Optika'}, {'id': 'deti', 'label': '🧸 Děti'},
        {'id': 'cestovani', 'label': '✈️ Cestování'}, {'id': 'kvetiny', 'label': '💐 Květiny'}, {'id': 'tisk', 'label': '🖨️ Tisk, trafika'},
    ],
    'shops': shops, 'offers': offers, 'news': news,
    'parking': {
        'hours': '7:00–24:00 (Cinema City do konce posledního představení, Max Fitness od 6:00)',
        'levels': 4, 'capacity': '500+', 'entrance': 'z ulice Jičínská',
        'rules': [
            {'when': 'Po–Pá 7:00–19:00', 'free': 60}, {'when': 'Po–Pá 19:00–7:00', 'free': 180}, {'when': 'Víkendy a svátky', 'free': 180},
        ],
        'rate': 60, 'rateUnit': 'Kč za každou započatou hodinu', 'bonus': 180,
        'bonusText': 'Zákazníci Cinema City, Max Fitness a Automyčky Express získají 3 hodiny zdarma navíc – lístek si nechte označit u pokladny.',
        'lostTicket': 1000, 'payment': ['Hotově nebo kartou v automatu', 'Bezkontaktně u výjezdové závory', 'Mobilem'],
        'longterm': 'Dlouhodobé a noční parkování (0:00–7:00): pourova@redstonegroup.cz, Po–Čt 9:00–17:00, Pá 9:00–16:00',
        'ev': {'where': 'úroveň −1: pravý vjezd, rovně a na konci chodby doprava', 'stations': ['2× 50 kW (CCS, CHAdeMO 50 kW, Mennekes 22 kW)', '1× 22 kW (2× Mennekes)'], 'operator': 'FUTUR/E/GO (ČEZ) – aplikace nebo čip, ceník na futurego.cz'},
    },
    'transport': {
        'metroClosed': {'from': '2026-02-02', 'until': '2027-02-28', 'text': 'Stanice metra A Flora je kvůli rekonstrukci (výměna eskalátorů, nové výtahy) uzavřena. Vlaky stanicí projíždějí. Předpokládané znovuotevření: konec února 2027.'},
        'trams': ['10', '11', '13', '16'],
        'alt': [
            {'from': 'Jiřího z Poděbrad (A)', 'how': 'tramvaj 13 (2 zastávky) nebo 10 min pěšky'},
            {'from': 'Želivského (A)', 'how': 'tramvaj 16 (2 zastávky) nebo 10 min pěšky'},
            {'from': 'Náměstí Míru (A)', 'how': 'tramvaje 10, 11, 16'},
        ],
        'stop': 'Flora (tramvaj a autobus přímo před centrem)', 'pid': '234 704 560',
    },
    'giftcard': {
        'where': 'Samoobslužný automat ve 2. podlaží, denně 7:00–24:00', 'payment': 'Pouze bezkontaktně kartou (hotovost nelze)',
        'range': [300, 6000], 'validity': '1 rok od nabití (nelze prodloužit)', 'balance': 'https://ocflora.giftify.me',
        'wallet': 'Kartu lze přidat do mobilní peněženky přes aplikaci Giftify', 'replace': 'Náhradní karta na Správě centra za 250 Kč (nutný doklad o koupi s číslem TOKEN)',
        'how': 'Platí se jako běžnou kartou (magnetický proužek nebo telefon), bez PINu, lze kombinovat s jinou platbou.',
    },
}
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('// Vygenerováno scripts/build-data.py z dat webu ocflora.cz – neupravovat ručně.\n')
    f.write('window.FLORA_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('shops', len(shops), 'offers', len(offers), 'news', len(news), 'bytes', len(json.dumps(data, ensure_ascii=False)))
