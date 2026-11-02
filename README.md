# OC Flora – průvodce centrem (prototyp)

Webová aplikace pro zákazníky obchodního centra **OC Flora** (Vinohradská 2828/151, Praha 3). Mobil-first, instalovatelná jako PWA, funguje i bez signálu v garážích. Bez frameworku: `index.html` + `style.css` + `app.js` + vygenerovaná data v `data.js`.

Neoficiální prototyp – data pocházejí z veřejného webu https://www.ocflora.cz/ (stav v `data.js` → `meta.updated`).

## Co zákazník dostane

| Obrazovka | Co řeší |
|---|---|
| **Dnes** | Je otevřeno? Dokdy? Pozdrav podle denní doby, upozornění na státní svátek (zákonné zavření prodejen nad 200 m²), co se dnes děje (soutěž, akce), uzavřené metro a náhradní tramvaje, aktuální nabídky, oblíbené obchody, co má otevřeno i po 21. hodině. Když běží hlídač parkování, ukazuje ho přímo nahoře. |
| **Obchody** | 127 obchodů a služeb. Hledání bez diakritiky (hledá i v popisu: „lekar“, „kava“, „sushi“), filtry podle kategorie, podlaží, „otevřeno teď“ a „přijímá dárkovou kartu“, abecední seznam s logem, podlažím a stavem (do 21:00 / zavírá za 15 min / zavřeno). |
| **Detail obchodu** | Stav a hodiny po dnech (dnešek zvýrazněný), podlaží, zavolat, web, e-mail, hvězdička do oblíbených, přidat do nákupního seznamu, nabídky prodejny, umístění na interaktivním plánu (iframe Simplaq od provozovatele). |
| **Jídlo a káva** | Food court ve 4. podlaží a kavárny v pasáži; rychlé filtry (káva, sladké, Asie, fast food, zdravě, česká, pečivo, polévky), otevřené řazené první, tlačítko **Vyber za mě**. |
| **Parkování** | Ceník (1 h / 3 h zdarma podle dne a času, 60 Kč za započatou hodinu, bonus +3 h pro kino/fitness/myčku, ztráta lístku), **hlídač parkovného**: zadáte čas příjezdu, úroveň a kde stojíte – aplikace počítá, dokdy je zdarma, kolik právě zaplatíte a kdy začne další hodina; připomínka 10 min předem; upozornění na zapomenuté hlídání. Nabíjení elektromobilů, platby, noční stání. |
| **Plán centra** | Podlaží −2 až 5 s popisem a seznamem obchodů v patře, interaktivní plán. |
| **Více** | Otevírací doba všech částí (pasáž, obchody, food court, Albert, kino, fitness), kontakt a navigace, doprava (uzavřené metro do února 2027, tramvaje 10/11/13/16, alternativní stanice), dárková karta (koupě, platba, zůstatek, výměna), Cinema City, akce a novinky, nabídky, oblíbené, nákupní seznam, vzhled (auto/světlý/tmavý), instalace na plochu. |

Vše osobní (oblíbené, parkování, seznam) zůstává jen v zařízení (`localStorage`, klíč `ocflora-app-v1`).

## Spuštění

```bash
python -X utf8 scripts/serve.py 5180
```

Poté otevřete http://localhost:5180/ (service worker vyžaduje http/https, ne `file://`). Vlastní server podporuje HTTP Range, bez kterého Chrome nepřehraje video spořiče; `python -m http.server` stačí na vše ostatní. V aplikaci Claude lze použít `.claude/launch.json` (konfigurace `flora-app`).

### Testování s jiným časem

Pro ověření stavů (zavírá za 15 min, neděle, svátek, parkovné) lze simulovat čas parametrem v adrese, např. `index.html?now=2026-12-24T13:00#/dnes`. Simulace se drží po dobu karty (sessionStorage) a v záhlaví svítí žlutý štítek **TEST**; zrušíte ji v **Více → Simulovaný čas → Zrušit**.

Příklady: `?now=2026-11-02T20:45` (zavírá za 15 min), `?now=2026-11-08T09:30` (neděle, otevírá v 10:00), `?now=2026-12-25T13:00` (státní svátek).

## Spořič obrazovky (video pro infopanely)

`assets/intro/intro.mp4` (1920×1080) a `intro-portrait.mp4` (1080×1920) je 26s smyčka: rozkvétající logo, 127 obchodů (plující loga), food court, IMAX, parkování a tramvaje, závěrečné „Vítejte na Floře“. `screensaver.js` ji přehraje hned při otevření aplikace a znovu po 30 s nečinnosti (`IDLE_MS`); dotyk, klepnutí, klávesa nebo posun ji skryjí. Na výšku se automaticky použije svislá verze (`?video=vyska` / `?video=sirka` orientaci přibije). Pokud prohlížeč automatické přehrání zakáže, zůstane zobrazený úvodní snímek s výzvou k dotyku. Ručně lze video spustit z **Více → Spořič obrazovky → Přehrát**.

Video se generuje skriptem (Pillow + numpy + resvg-py + ffmpeg):

```bash
python -X utf8 scripts/render-intro.py
python -X utf8 scripts/render-intro.py --portrait
```

Náhledy jednotlivých okamžiků: `python -X utf8 scripts/render-intro.py --preview 3 6.5 11.5 16 20.5 24.6 --out <složka>`. Texty, časování scén a výběr log jsou nahoře ve skriptu (`T`, `S_*`, `SHOP_IDS`, `FOOD_IDS`).

## Aktualizace dat z ocflora.cz

```bash
python -X utf8 scripts/scrape-ocflora.py data/raw-ocflora.json
python -X utf8 scripts/sync-logos.py data/raw-ocflora.json
python -X utf8 scripts/optimize-logos.py
python -X utf8 scripts/build-data.py data/raw-ocflora.json data.js
```

- `scrape-ocflora.py` projde sitemapy webu (`obchod`, `nabidka`, `aktualita`) a stáhne detaily všech obchodů (kategorie, hodiny, podlaží, dárková karta, kontakty, popis, ID jednotky na plánu), nabídek a aktualit.
- `sync-logos.py` stáhne loga do `assets/logos/`; `optimize-logos.py` převede SVG s vloženým rastrem (až 2 MB) na malé PNG.
- `build-data.py` převede hodiny na týdenní pole v minutách, přiřadí štítky kuchyní/služeb (`TAGS`), termíny akcí (`EVENTS`), ponechá nabídky od září 2026 a doplní ručně ověřené informace (parkování, doprava, dárková karta, podlaží). Po změně webu je potřeba zkontrolovat `EVENTS` a texty v `data` na konci skriptu.

## Omezení prototypu

- Data jsou statický snímek; neaktualizují se automaticky. Otevírací doby o svátcích web neuvádí – aplikace zobrazuje jen obecné upozornění podle zákona o prodejní době.
- Linky MHD a termín znovuotevření metra vycházejí z informací PID a ocflora.cz k datu snímku.
- Připomínka parkování funguje spolehlivě jen při otevřené aplikaci (bez serveru nelze posílat push notifikace).
- Interaktivní plán je iframe třetí strany (atriumflora.mysimplaq.com); bez připojení se nenačte.
- Není to oficiální aplikace OC Flora; před nasazením je nutný souhlas provozovatele s použitím dat a log.
