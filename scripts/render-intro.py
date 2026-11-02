# -*- coding: utf-8 -*-
"""Render the OC Flora screensaver video (assets/intro/intro.mp4, 1920x1080) and its portrait cut
(assets/intro/intro-portrait.mp4, 1080x1920 for vertical info panels).

Uses the shop logos in assets/logos and data.js. Requires Pillow, numpy, resvg-py and ffmpeg on PATH.
Usage:
  python -X utf8 scripts/render-intro.py                 # landscape
  python -X utf8 scripts/render-intro.py --portrait      # portrait
  python -X utf8 scripts/render-intro.py --preview 1.5 6 11 15 20 24   # PNG stills into scratch dir
"""
import json, math, random, subprocess, sys, tempfile, re
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'intro'
CACHE = Path(tempfile.gettempdir()) / 'ocflora-logo-cache'
PORTRAIT = '--portrait' in sys.argv
W, H = (1080, 1920) if PORTRAIT else (1920, 1080)
FPS, DURATION = 30, 26.0
NAME = 'intro-portrait' if PORTRAIT else 'intro'
FONT = 'C:/Windows/Fonts/bahnschrift.ttf'

WINE = np.array([108, 29, 69]) / 255
WINE_DARK = np.array([52, 4, 30]) / 255
WINE_LIGHT = np.array([151, 63, 104]) / 255
ROSE = np.array([181, 153, 168]) / 255
GOLD = np.array([246, 196, 83]) / 255
CREAM = np.array([246, 241, 243]) / 255
WHITE = np.ones(3)

# ---- scénář (sekundy) ----
S_SHOPS, S_FOOD, S_FUN, S_PARK, S_OUTRO = 4.0, 9.0, 13.5, 18.0, 22.0
CUTS = [S_SHOPS, S_FOOD, S_FUN, S_PARK, S_OUTRO]
XF = 0.6  # délka prolnutí

rng = random.Random(11)
DATA = json.loads((ROOT / 'data.js').read_text(encoding='utf-8').split('= ', 1)[1].rstrip(';\n'))
SHOPS = DATA['shops']

# ---------- pomocné ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def out_expo(x): return 1 if x >= 1 else 1 - 2 ** (-10 * x)
def out_cubic(x): return 1 - (1 - x) ** 3
def in_out(x): return 3 * x * x - 2 * x * x * x
def out_back(x, s=1.7): x -= 1; return 1 + x * x * ((s + 1) * x + s)

def font(size, style='Bold'):
    f = ImageFont.truetype(FONT, size)
    try: f.set_variation_by_name(style)
    except Exception: pass
    return f

def to_sprite(img):
    a = np.asarray(img.convert('RGBA'), dtype=np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    return a

def blit(dst, spr, x, y, op=1.0):
    x, y = int(round(x)), int(round(y))
    h, w = spr.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1 or op <= 0: return
    s = spr[y0 - y:y1 - y, x0 - x:x1 - x]
    d = dst[y0:y1, x0:x1]
    d *= 1 - s[..., 3:4] * op
    d += s[..., :3] * op

def add(dst, spr, x, y, op=1.0):
    x, y = int(round(x)), int(round(y))
    h, w = spr.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1 or op <= 0: return
    dst[y0:y1, x0:x1] += spr[y0 - y:y1 - y, x0 - x:x1 - x, :3] * op

def text_sprite(text, size, color=(255, 255, 255), style='Bold', spacing=0):
    f = font(size, style)
    chars = list(text)
    widths = [f.getlength(c) for c in chars]
    tw = int(sum(widths) + spacing * max(len(chars) - 1, 0)) + 12
    asc, desc = f.getmetrics()
    img = Image.new('L', (tw, asc + desc + 12), 0)
    d = ImageDraw.Draw(img)
    x = 6
    for c, cw in zip(chars, widths):
        d.text((x, 6), c, font=f, fill=255); x += cw + spacing
    img = img.crop(img.getbbox())
    rgba = Image.new('RGBA', img.size, tuple(int(c) for c in color) + (255,)); rgba.putalpha(img)
    return to_sprite(rgba)

def glow_of(spr, radius, color):
    a = Image.fromarray((spr[..., 3] * 255).astype(np.uint8))
    pad = radius * 3
    big = Image.new('L', (a.width + pad * 2, a.height + pad * 2)); big.paste(a, (pad, pad))
    big = big.filter(ImageFilter.GaussianBlur(radius))
    g = np.asarray(big, np.float32)[..., None] / 255
    return np.concatenate([g * color, g * 0], axis=2).astype(np.float32), pad

def reveal(spr, p):
    w = int(spr.shape[1] * clamp(p))
    return spr[:, :w] if w > 0 else None

def center_blit(f, spr, y, op=1.0, p=1.0, dy=0.0, cx=None):
    s = reveal(spr, p)
    if s is not None: blit(f, s, (W / 2 if cx is None else cx) - spr.shape[1] / 2, y + dy, op)

def col(c): return tuple(int(round(v * 255)) for v in c)

# ---------- loga → dlaždice ----------
def logo_png(shop):
    """Rastr loga (RGBA PIL) – SVG přes resvg, PNG přímo; cache v temp."""
    src = ROOT / shop['logo']
    if not src.exists(): return None
    if src.suffix == '.png': return Image.open(src).convert('RGBA')
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / (src.stem + '.png')
    if not out.exists():
        try:
            import resvg_py
            svg = src.read_text(encoding='utf-8', errors='replace')
            out.write_bytes(bytes(resvg_py.svg_to_bytes(svg_string=svg, width=900)))
        except Exception as e:
            print('  svg fail', src.name, e); return None
    return Image.open(out).convert('RGBA')

def make_tile(shop, tw=300, th=180, pad=30):
    """Bílá zaoblená dlaždice s logem a měkkým stínem (RGBA sprite)."""
    im = logo_png(shop)
    dark = shop.get('logoDark')
    r = 24; sh = 28  # radius, shadow
    tile = Image.new('RGBA', (tw + sh * 2, th + sh * 2 + 10), (0, 0, 0, 0))
    shadow = Image.new('L', tile.size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle([sh, sh + 10, sh + tw, sh + th + 10], radius=r, fill=120)
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    tile.putalpha(shadow)
    bgc = (43, 34, 51, 255) if dark else (255, 255, 255, 255)
    card = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle([0, 0, tw - 1, th - 1], radius=r, fill=bgc)
    if im is not None:
        bbox = im.getbbox()
        if bbox: im = im.crop(bbox)
        # bílá loga na bílé dlaždici: zjisti průměrný jas neprůhledných pixelů
        arr = np.asarray(im, np.float32)
        if arr[..., 3].max() > 0 and not dark:
            m = arr[..., 3] > 40
            white_share = ((arr[..., :3][m].min(axis=1) > 225).mean()) if m.any() else 0
            if m.any() and (arr[..., :3][m].mean() > 235 or white_share > 0.5): bgc = (43, 34, 51, 255); ImageDraw.Draw(card).rounded_rectangle([0, 0, tw - 1, th - 1], radius=r, fill=bgc)
        sc = min((tw - pad * 2) / im.width, (th - pad * 2) / im.height)
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
        card.alpha_composite(im, ((tw - im.width) // 2, (th - im.height) // 2))
    else:
        d = ImageDraw.Draw(card); f = font(44, 'Bold')
        name = shop['name'][:14]
        tb = d.textbbox((0, 0), name, font=f)
        d.text(((tw - (tb[2] - tb[0])) / 2, (th - (tb[3] - tb[1])) / 2 - 8), name, font=f, fill=col(WINE))
    tile.alpha_composite(card, (sh, sh))
    return to_sprite(tile)

print('Preparing tiles...')
by_id = {s['id']: s for s in SHOPS}
def pick(ids): return [by_id[i] for i in ids if i in by_id]
SHOP_IDS = ['hm', 'sephora', 'intersport', 'lindex', 'tatuum', 'pandora', 'albert-supermarket', 'dm-drogerie', 'normal', 'luxor', 'albi', 'tescoma',
            'gant', 'ecco', 'skechers', 'bata', 'calzedonia', 'tchibo', 'flying-tiger-copenhagen', 'istores-apple-premium-partner', 'yves-rocher', 'loccitane',
            'manufaktura', 'wittchen', 'medicine', 'triumph', 'butlers', 'bambule', 'keen', 'benu-lekarna', 'dr-max-lekarna', 'apart', 'yes-klenoty', 'lindt', 'bushman', 'grandoptical']
FOOD_IDS = ['starbucks', 'costa-coffee', 'mcdonalds', 'kfc', 'ginza-running-sushi', 'pai-thai', 'bombay-express', 'ugo-salaterie', 'prima-basta', 'wok-dej',
            'poke-fun', 'pholevka', 'bageterie-boulevard', 'armins-cake', 'ovocny-svetozor', 'paul-stanek', 'fruitisimo-fresh-bar', 'loving-bistro']
TILES_SHOPS = [make_tile(s) for s in pick(SHOP_IDS)]
TILES_FOOD = [make_tile(s, 300, 200) for s in pick(FOOD_IDS)]
print(f'  {len(TILES_SHOPS)} shop tiles, {len(TILES_FOOD)} food tiles')

# ---------- květ (logo) ----------
PETALS = [(64, 34), (92, 54), (81, 88), (47, 88), (36, 54)]  # ve 128px souřadnicích
def flower_sprite(size, petal_scales, core=True, color=WHITE, core_color=WINE, dot=GOLD, soft=0):
    """Květ OC Flora – každý okvětní lístek s vlastním měřítkem (0..1)."""
    S = size; k = S / 128
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for (px, py), ps in zip(PETALS, petal_scales):
        if ps <= 0: continue
        cx, cy = 64 + (px - 64) * (0.6 + 0.4 * ps), 64 + (py - 64) * (0.6 + 0.4 * ps)
        r = 19 * ps
        d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=col(color) + (255,))
    if core:
        d.ellipse([(64 - 15) * k, (64 - 15) * k, (64 + 15) * k, (64 + 15) * k], fill=col(core_color) + (255,))
        d.ellipse([(64 - 7) * k, (64 - 7) * k, (64 + 7) * k, (64 + 7) * k], fill=col(dot) + (255,))
    if soft: im = im.filter(ImageFilter.GaussianBlur(soft))
    return to_sprite(im)

LOGO_SIZE = 560 if PORTRAIT else 420
LOGO = flower_sprite(LOGO_SIZE, [1] * 5)
LOGO_GLOW, LOGO_GLOW_PAD = glow_of(LOGO, 40, GOLD * 0.5 + ROSE * 0.3)
LOGO_SMALL = flower_sprite(72, [1] * 5)
BIG_FLOWER = Image.new('L', (1600, 1600), 0)
_d = ImageDraw.Draw(BIG_FLOWER); _k = 1600 / 128
for px, py in PETALS: _d.ellipse([(px - 19) * _k, (py - 19) * _k, (px + 19) * _k, (py + 19) * _k], outline=255, width=3)
BIG_FLOWER = BIG_FLOWER.filter(ImageFilter.GaussianBlur(1.5))

def big_flower(angle, op):
    r = np.asarray(BIG_FLOWER.rotate(angle, resample=Image.BILINEAR), np.float32)[..., None] / 255
    return np.concatenate([r * (ROSE * 0.9) * op, r * 0], axis=2)

# ---------- texty ----------
def eyebrow(t, color=GOLD, size=30): return text_sprite(t, size, col(color), 'SemiBold', spacing=10)
def headline(t, size): return text_sprite(t, size, (255, 255, 255), 'Bold', spacing=2)
def sub(t, size=38): return text_sprite(t, size, col(CREAM * 0.92), 'Light', spacing=1)

HL = 112 if PORTRAIT else 118
T = dict(
    eyebrow=eyebrow('NÁKUPNÍ CENTRUM  ·  VINOHRADY  ·  PRAHA 3', GOLD, 24 if PORTRAIT else 30),
    brand=text_sprite('OC FLORA', 128 if PORTRAIT else 190, (255, 255, 255), 'SemiBold', spacing=16 if PORTRAIT else 22),
    shops_eb=eyebrow('OBCHODY A SLUŽBY'),
    food_eb=eyebrow('FOOD COURT  ·  4. PODLAŽÍ'),
    fun_eb=eyebrow('ZÁBAVA  ·  4. A 5. PODLAŽÍ'),
    park_eb=eyebrow('PARKOVÁNÍ A DOPRAVA'),
    outro_eb=eyebrow('TĚŠÍME SE NA VÁS'),
    touch=text_sprite('DOTKNĚTE SE OBRAZOVKY', 30, col(WINE_DARK), 'Bold', spacing=8),
)
if PORTRAIT:
    T['shops_h'] = [headline('127 OBCHODŮ', HL), headline('POD JEDNOU', HL), headline('STŘECHOU', HL)]
    T['shops_s'] = [sub('Po–So 9:00–21:00  ·  Ne 10:00–21:00'), sub('Albert a food court denně do 24:00')]
    T['food_h'] = [headline('CHUTĚ', HL), headline('Z CELÉHO', HL), headline('SVĚTA', HL)]
    T['food_s'] = [sub('18 restaurací a kaváren'), sub('denně 8:00–24:00')]
    T['fun_h'] = [headline('JEDINÉ', HL), headline('3D IMAX', HL), headline('V ČESKU', HL)]
    T['fun_s'] = [sub('Cinema City  ·  8 sálů'), sub('Max Fitness  ·  2 500 m²  ·  od 6:00')]
    T['park_h'] = [headline('1 HODINA', HL), headline('PARKOVÁNÍ', HL), headline('ZDARMA', HL)]
    T['park_s'] = [sub('500+ míst  ·  vjezd z Jičínské'), sub('večer a o víkendu 3 hodiny zdarma')]
    T['outro_h'] = [headline('VÍTEJTE', 150), headline('NA FLOŘE', 150)]
else:
    T['shops_h'] = [headline('127 OBCHODŮ A SLUŽEB', HL)]
    T['shops_s'] = [sub('pod jednou střechou  ·  Po–So 9:00–21:00  ·  Ne 10:00–21:00')]
    T['food_h'] = [headline('CHUTĚ Z CELÉHO SVĚTA', HL)]
    T['food_s'] = [sub('18 restaurací a kaváren  ·  food court ve 4. podlaží  ·  denně 8:00–24:00')]
    T['fun_h'] = [headline('JEDINÉ 3D IMAX V ČESKU', HL)]
    T['fun_s'] = [sub('Cinema City  ·  8 sálů  ·  4. podlaží      Max Fitness  ·  2 500 m²  ·  5. podlaží')]
    T['park_h'] = [headline('1 HODINA PARKOVÁNÍ ZDARMA', HL)]
    T['park_s'] = [sub('500+ míst  ·  vjezd z Jičínské  ·  večer a o víkendu 3 hodiny zdarma')]
    T['outro_h'] = [headline('VÍTEJTE NA FLOŘE', 150)]
TRAMS = [text_sprite(n, 64, col(WINE_DARK), 'Bold') for n in ('10', '11', '13', '16')]
T_TRAM_EB = eyebrow('TRAMVAJE PŘÍMO U CENTRA', CREAM * 0.9, 26)
CHIP_TXT = [text_sprite(s, 30, col(WINE_DARK), 'SemiBold', spacing=3) for s in ('ASIE', 'ČESKÁ KUCHYNĚ', 'KÁVA', 'SLADKÉ', 'FAST FOOD', 'ZDRAVĚ')]

def chip(txt_spr, color=GOLD, padx=26, pady=14):
    h, w = txt_spr.shape[:2]
    im = Image.new('RGBA', (w + padx * 2, h + pady * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=col(color) + (255,))
    spr = to_sprite(im); blit_into(spr, txt_spr, padx, pady); return spr

def blit_into(dst, spr, x, y):
    h, w = spr.shape[:2]
    d = dst[y:y + h, x:x + w]
    d *= 1 - spr[..., 3:4]; d += spr
CHIPS = [chip(c, GOLD if i % 2 == 0 else CREAM) for i, c in enumerate(CHIP_TXT)]
TRAM_BADGES = [chip(t, GOLD, 30, 16) for t in TRAMS]

# ---------- pozadí ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
nx, ny = (xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)
rad = np.sqrt(nx ** 2 * (0.75 if not PORTRAIT else 1.1) + (ny + 0.1) ** 2)
base = WINE_DARK * 0.85 + (WINE - WINE_DARK) * np.clip(1.15 - rad, 0, 1)[..., None] * 1.05
vign = np.clip(1 - 0.5 * (nx ** 2 * 0.6 + ny ** 2 * 0.9), 0.25, 1)[..., None]
noise = np.asarray(Image.effect_noise((W // 3, H // 3), 30).resize((W, H), Image.BICUBIC), np.float32)[..., None] / 255
BG = (base * vign * (0.9 + 0.2 * noise)).astype(np.float32)
# teplý odlesk nahoře
BG += (GOLD * 0.08)[None, None] * np.clip(1 - np.sqrt((nx - 0.6) ** 2 + (ny + 1.1) ** 2) / 1.1, 0, 1)[..., None]

def soft_disc(r, color):
    s = r * 2 + 2
    yy2, xx2 = np.mgrid[0:s, 0:s] - r
    d = np.sqrt(xx2 ** 2 + yy2 ** 2) / r
    a = np.clip(1 - d, 0, 1) ** 1.6
    return np.concatenate([a[..., None] * color, a[..., None] * 0], axis=2).astype(np.float32)
BOKEH = [(soft_disc(r, GOLD * 0.9 if i % 3 else ROSE), rng.uniform(0, W), rng.uniform(0, H), rng.uniform(8, 20), rng.uniform(0, 6.28), 0.04 + rng.uniform(0, 0.05))
         for i, r in enumerate([rng.randrange(60, 220) for _ in range(14)])]
DOTS = [soft_disc(r, WHITE * 0.7 + GOLD * 0.5) for r in (2, 3, 5)]
SPARK = [[rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.3, 1)] for _ in range(90)]

def backdrop(f, t):
    for spr, x, y, speed, ph, op in BOKEH:
        px = (x + math.sin(t * 0.13 + ph) * 90) % (W + 400) - 200
        py = (y - t * speed) % (H + 400) - 200
        add(f, spr, px - spr.shape[1] / 2, py - spr.shape[0] / 2, op * (0.8 + 0.2 * math.sin(t * 0.9 + ph)))
    add(f, big_flower(t * 2.5, 0.16), W * (0.72 if not PORTRAIT else 0.5) - 800, H * 0.5 - 800 + math.sin(t * 0.3) * 20)
    for x, y, z in SPARK:
        px = (x + math.sin(t * 0.5 + y) * 25) % W; py = (y - t * 18 * z) % H
        add(f, DOTS[0 if z < 0.7 else 1], px, py, 0.35 * z)

_bands = {}
def legibility_band(f, y0, y1, strength=0.55):
    key = (y0, y1, strength)
    if key not in _bands:
        a = np.clip(np.minimum((yy - y0) / 90, (y1 - yy) / 90), 0, 1)[..., None] * strength
        _bands[key] = (1 - a, WINE_DARK[None, None] * a * 0.9)
    m, c = _bands[key]
    f *= m; f += c

# ---------- scény ----------
def rows_of_tiles(f, lt, tiles, rows, y_top, gap_y, speed, tile_op, scale=1.0):
    """Pásy dlaždic plující v protisměru (paralaxa)."""
    n = len(tiles)
    for r in range(rows):
        dir_ = 1 if r % 2 == 0 else -1
        spr0 = tiles[0]; th, tw = spr0.shape[:2]
        tw_s = int(tw * scale)
        step = tw_s + 24
        off = (lt * speed * (0.75 + 0.25 * (r % 3)) * dir_ + r * 170) % step
        y = y_top + r * (int(th * scale) + gap_y)
        count = W // step + 3
        for i in range(-1, count):
            spr = tiles[(i + r * 7) % n]
            if scale != 1.0: spr = cache_scaled(spr, scale)
            x = i * step + off - step
            blit(f, spr, x, y, tile_op)

_scaled = {}
def cache_scaled(spr, scale):
    key = (id(spr), round(scale, 3))
    if key not in _scaled:
        h, w = spr.shape[:2]
        im = Image.fromarray(np.clip(np.concatenate([spr[..., :3] / np.maximum(spr[..., 3:4], 1e-3), spr[..., 3:4]], 2) * 255, 0, 255).astype(np.uint8), 'RGBA')
        _scaled[key] = to_sprite(im.resize((int(w * scale), int(h * scale)), Image.LANCZOS))
    return _scaled[key]

def draw_block(f, lt, eb, heads, subs, y, t0=0.2, cx=None, align='center'):
    """Eyebrow + nadpisy + podtitulky s postupným odhalením. Vrací spodní y."""
    cx = W / 2 if cx is None else cx
    a = out_expo(prog(lt, t0, t0 + 0.6))
    if a > 0:
        line = int(90 * a)
        f[int(y) + 14:int(y) + 17, int(cx - line / 2):int(cx + line / 2)] += GOLD * 0.9
        center_blit(f, eb, y + 32, a, 1.0, (1 - a) * 16, cx)
    yy0 = y + 95
    for k, h in enumerate(heads):
        p = prog(lt, t0 + 0.25 + k * 0.18, t0 + 0.95 + k * 0.18)
        center_blit(f, h, yy0, 1.0, out_expo(p), (1 - out_expo(p)) * 26, cx)
        yy0 += h.shape[0] + 14
    yy0 += 12
    for k, s in enumerate(subs):
        p = prog(lt, t0 + 0.8 + k * 0.15, t0 + 1.4 + k * 0.15)
        if p > 0: center_blit(f, s, yy0, p, 1.0, (1 - out_cubic(p)) * 18, cx)
        yy0 += s.shape[0] + 16
    return yy0

def scene_intro(f, t):
    lt = t
    cx, cy = W / 2, (H * 0.40 if PORTRAIT else H * 0.40)
    # paprsky lístků – každý rozkvete zvlášť
    scales = [out_back(prog(lt, 0.35 + i * 0.13, 1.0 + i * 0.13), 1.6) for i in range(5)]
    core_p = prog(lt, 0.95, 1.4)
    size = LOGO_SIZE
    spr = flower_sprite(size, scales, core=core_p > 0, core_color=WINE_DARK + (WINE - WINE_DARK) * core_p, dot=GOLD * core_p + WINE * (1 - core_p))
    if lt > 1.3: add(f, LOGO_GLOW, cx - size / 2 - LOGO_GLOW_PAD, cy - size / 2 - LOGO_GLOW_PAD, (0.55 + 0.2 * math.sin(lt * 2)) * prog(lt, 1.3, 2.0))
    blit(f, spr, cx - size / 2, cy - size / 2)
    # odlesk přes květ
    gp = prog(lt, 1.9, 2.7)
    if 0 < gp < 1:
        band = Image.new('L', (size, size), 0); d = ImageDraw.Draw(band)
        bx = -200 + gp * (size + 400)
        d.polygon([(bx, 0), (bx + 70, 0), (bx - 90, size), (bx - 160, size)], fill=255)
        band = np.asarray(band.filter(ImageFilter.GaussianBlur(12)), np.float32) / 255
        g = (band * spr[..., 3])[..., None]
        x0, y0 = int(cx - size / 2), int(cy - size / 2)
        f[y0:y0 + size, x0:x0 + size] += g * (GOLD * 0.5 + WHITE * 0.3)
    # název
    by = cy + size / 2 + (40 if PORTRAIT else 30)
    a = out_expo(prog(lt, 1.2, 2.0))
    center_blit(f, T['brand'], by, 1.0, a, (1 - a) * 30)
    e = prog(lt, 1.9, 2.6)
    if e > 0:
        ln = int((T['brand'].shape[1] * 0.9) * out_expo(e))
        f[int(by) + T['brand'].shape[0] + 26:int(by) + T['brand'].shape[0] + 28, int(cx - ln / 2):int(cx + ln / 2)] += GOLD * 0.9
        center_blit(f, T['eyebrow'], by + T['brand'].shape[0] + 48, e, 1.0, (1 - out_cubic(e)) * 14)
    fl = 1 - prog(lt, 1.0, 1.5)
    if 0.95 < lt: f += (GOLD * 0.35 + WHITE * 0.25) * max(0, fl) ** 2 * 0.6

def scene_shops(f, t):
    lt = t - S_SHOPS
    e = out_expo(prog(lt, 0, 1.2))
    if PORTRAIT:
        rows_of_tiles(f, lt + 6, TILES_SHOPS, 4, int(H * 0.42) + int((1 - e) * 200), 22, 55, 0.95 * e, 1.0)
        legibility_band(f, -200, int(H * 0.40), 0.35)
        draw_block(f, lt, T['shops_eb'], T['shops_h'], T['shops_s'], H * 0.10)
    else:
        rows_of_tiles(f, lt + 6, TILES_SHOPS, 2, int(H * 0.53) + int((1 - e) * 200), 26, 70, 0.95 * e, 0.98)
        legibility_band(f, -200, int(H * 0.5), 0.35)
        draw_block(f, lt, T['shops_eb'], T['shops_h'], T['shops_s'], H * 0.12)

def scene_food(f, t):
    lt = t - S_FOOD
    e = out_expo(prog(lt, 0, 1.2))
    # mřížka jídla, pomalý zoom
    sc = (0.78 if PORTRAIT else 0.88) * (1 + lt * 0.01)
    spr0 = cache_scaled(TILES_FOOD[0], sc); th, tw = spr0.shape[:2]
    cols = 4 if PORTRAIT else 7
    rows = 3 if PORTRAIT else 2
    gx, gy = tw + 18, th + 18
    x0 = W / 2 - (cols * gx) / 2 + 9 + math.sin(lt * 0.4) * 30
    y0 = (H * 0.50 if PORTRAIT else H * 0.47) + (1 - e) * 240
    k = 0
    for r in range(rows):
        for c in range(cols):
            spr = cache_scaled(TILES_FOOD[(k * 5) % len(TILES_FOOD)], sc); k += 1
            d = prog(lt, 0.05 * (c + r * 2), 0.5 + 0.05 * (c + r * 2))
            blit(f, spr, x0 + c * gx + (r % 2) * gx * 0.5 - gx * 0.25, y0 + r * gy + (1 - out_expo(d)) * 60, out_expo(d) * 0.96)
    legibility_band(f, -200, int(H * (0.46 if PORTRAIT else 0.44)), 0.4)
    yb = draw_block(f, lt, T['food_eb'], T['food_h'], T['food_s'], H * 0.08 if PORTRAIT else H * 0.11)
    # chipy kuchyní
    for i, ch in enumerate(CHIPS):
        p = out_back(prog(lt, 1.5 + i * 0.12, 2.1 + i * 0.12), 1.2)
        if p <= 0: continue
        total = sum(c.shape[1] for c in CHIPS) + 16 * (len(CHIPS) - 1)
        if PORTRAIT:
            row = 0 if i < 3 else 1
            items = CHIPS[:3] if row == 0 else CHIPS[3:]
            total = sum(c.shape[1] for c in items) + 16 * (len(items) - 1)
            xs = W / 2 - total / 2 + sum(c.shape[1] + 16 for c in items[:i - (0 if row == 0 else 3)])
            y = yb + 20 + row * 72
        else:
            xs = W / 2 - total / 2 + sum(c.shape[1] + 16 for c in CHIPS[:i]); y = yb + 18
        blit(f, cache_scaled(ch, max(0.05, p)) if p < 0.999 else ch, xs + ch.shape[1] * (1 - p) / 2, y + ch.shape[0] * (1 - p) / 2, clamp(p))

def make_rays(size, n):
    im = Image.new('L', (size, size), 0); d = ImageDraw.Draw(im); c = size / 2
    for i in range(n):
        a0 = i * 2 * math.pi / n; a1 = a0 + math.pi / n * 0.5
        d.polygon([(c, c), (c + math.cos(a0) * c * 1.5, c + math.sin(a0) * c * 1.5), (c + math.cos(a1) * c * 1.5, c + math.sin(a1) * c * 1.5)], fill=255)
    im = im.filter(ImageFilter.GaussianBlur(14))
    yy2, xx2 = np.mgrid[0:size, 0:size]; r = np.sqrt((xx2 - c) ** 2 + (yy2 - c) ** 2) / c
    return Image.fromarray((np.asarray(im, np.float32) * np.clip(1 - r, 0, 1) ** 1.3).astype(np.uint8))
RAYS = make_rays(1900, 16)
def rays_sprite(angle, op, color):
    r = np.asarray(RAYS.rotate(angle, resample=Image.BILINEAR), np.float32)[..., None] / 255
    return np.concatenate([r * color * op, r * 0], axis=2)

FRAMES = []  # filmová okénka
for i in range(5 if PORTRAIT else 6):
    fw, fh = (300, 170) if not PORTRAIT else (260, 150)
    im = Image.new('RGBA', (fw + 40, fh + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, 20 + fw, 20 + fh], radius=10, outline=col(GOLD) + (230,), width=3, fill=col(WINE_DARK) + (160,))
    for k in range(6):
        d.rectangle([34 + k * (fw - 20) / 6, 8, 34 + k * (fw - 20) / 6 + 20, 16], fill=col(GOLD) + (200,))
        d.rectangle([34 + k * (fw - 20) / 6, fh + 24, 34 + k * (fw - 20) / 6 + 20, fh + 32], fill=col(GOLD) + (200,))
    FRAMES.append(to_sprite(im))

def scene_fun(f, t):
    lt = t - S_FUN
    cx, cy = (W / 2, H * 0.68) if PORTRAIT else (W * 0.5, H * 0.72)
    add(f, rays_sprite(lt * 6, 0.5 * prog(lt, 0, 1.0) * (0.85 + 0.15 * math.sin(lt * 3)), GOLD * 0.8 + ROSE * 0.3), cx - 950, cy - 950)
    # filmová okénka obíhající
    for i, fr in enumerate(FRAMES):
        ang = lt * 0.35 + i * (2 * math.pi / len(FRAMES))
        rx, ry = (430, 520) if PORTRAIT else (780, 330)
        x = cx + math.cos(ang) * rx - fr.shape[1] / 2; y = cy + math.sin(ang) * ry * 0.75 - fr.shape[0] / 2 + 40
        depth = 0.6 + 0.4 * (math.sin(ang) + 1) / 2
        blit(f, cache_scaled(fr, 0.7 + 0.5 * depth), x, y, prog(lt, 0.3 + i * 0.05, 0.9 + i * 0.05) * (0.3 + 0.45 * depth))
    legibility_band(f, -200, int(H * (0.42 if PORTRAIT else 0.46)), 0.45)
    draw_block(f, lt, T['fun_eb'], T['fun_h'], T['fun_s'], H * 0.08 if PORTRAIT else H * 0.11)
    # IMAX „plátno“ – zlatý obdélník s odleskem
    p = out_expo(prog(lt, 0.9, 1.7))
    if p > 0:
        sw, sh = (int(W * 0.72 * p), int(H * 0.17)) if PORTRAIT else (int(W * 0.34 * p), int(H * 0.26))
        sx, sy = int(cx - sw / 2), int(cy - sh / 2)
        if sw > 4:
            f[sy:sy + sh, sx:sx + sw] = f[sy:sy + sh, sx:sx + sw] * 0.35 + WINE_DARK * 0.65
            f[sy - 3:sy, sx:sx + sw] += GOLD; f[sy + sh:sy + sh + 3, sx:sx + sw] += GOLD
            f[sy:sy + sh, sx - 3:sx] += GOLD; f[sy:sy + sh, sx + sw:sx + sw + 3] += GOLD
            gl = (math.sin(lt * 1.2) + 1) / 2
            f[sy:sy + sh, sx:sx + sw] += (GOLD * 0.12)[None, None] * np.clip(1 - np.abs(np.linspace(-1, 1, sw) - (gl * 2 - 1)) * 1.8, 0, 1)[None, :, None]
            if p > 0.95:
                imx = text_sprite('IMAX', 118 if PORTRAIT else 150, col(WHITE), 'Bold', spacing=14)
                center_blit(f, imx, cy - imx.shape[0] / 2 - 6, prog(lt, 1.6, 2.1))
                three = eyebrow('3D  ·  LASER  ·  12 KANÁLŮ ZVUKU', CREAM, 24)
                center_blit(f, three, cy + imx.shape[0] / 2 + 4, prog(lt, 1.9, 2.4))

def scene_park(f, t):
    lt = t - S_PARK
    # perspektivní „garáž“: linie ubíhající do dálky
    horizon = H * (0.56 if PORTRAIT else 0.52)
    lines = Image.new('L', (W, H), 0); d = ImageDraw.Draw(lines)
    for i in range(-12, 13):
        d.line([(W / 2 + i * 30, horizon), (W / 2 + i * (520 if PORTRAIT else 700), H + 100)], fill=70, width=2)
    for k in range(1, 9):
        yk = horizon + ((k + (lt * 0.9) % 1) ** 2.2) * (H - horizon) / 40
        if yk < H: d.line([(0, yk), (W, yk)], fill=int(40 + 90 * (k / 9)), width=2 + k // 3)
    arr = np.asarray(lines.filter(ImageFilter.GaussianBlur(1.0)), np.float32)[..., None] / 255
    f += arr * (ROSE * 0.6 + GOLD * 0.2) * prog(lt, 0, 1.0)
    # zlatý „reflektor“ auta projíždějící
    p = prog(lt, 0.5, 2.4)
    if 0 < p < 1:
        px = -300 + out_cubic(p) * (W + 600); py = horizon + 140 + p * 90
        tail = Image.new('L', (W, H), 0); dd = ImageDraw.Draw(tail)
        for ln, wd, fill in ((700, 4, 90), (380, 10, 150), (160, 20, 255)):
            dd.line([(px - ln, py + ln * 0.08), (px, py)], fill=fill, width=wd)
        tail = np.asarray(tail.filter(ImageFilter.GaussianBlur(4)), np.float32)[..., None] / 255
        f += tail * (GOLD * 0.8 + WHITE * 0.4)
    legibility_band(f, -200, int(horizon) - 20, 0.3)
    yb = draw_block(f, lt, T['park_eb'], T['park_h'], T['park_s'], H * 0.08 if PORTRAIT else H * 0.11)
    # velké P
    bigp = text_sprite('P', 520 if PORTRAIT else 420, col(GOLD), 'Bold')
    pp = out_back(prog(lt, 0.4, 1.2), 1.1)
    if pp > 0:
        s = cache_scaled(bigp, max(0.05, pp)) if pp < 0.999 else bigp
        bx, by = (W / 2 - s.shape[1] / 2, H * 0.66 - s.shape[0] / 2) if PORTRAIT else (W * 0.5 - s.shape[1] / 2, H * 0.655 - s.shape[0] / 2)
        gl, gpad = glow_of(s, 30, GOLD * 0.8)
        add(f, gl, bx - gpad, by - gpad, 0.5 * clamp(pp))
        blit(f, s, bx, by, clamp(pp))
    # tramvaje
    a = prog(lt, 1.6, 2.2)
    if a > 0:
        total = sum(b.shape[1] for b in TRAM_BADGES) + 18 * 3
        ty = H * 0.88 if PORTRAIT else H * 0.90
        center_blit(f, T_TRAM_EB, ty - 60, a)
        x = W / 2 - total / 2
        for i, b in enumerate(TRAM_BADGES):
            q = out_back(prog(lt, 1.8 + i * 0.12, 2.3 + i * 0.12), 1.3)
            if q > 0:
                s = cache_scaled(b, max(0.05, q)) if q < 0.999 else b
                blit(f, s, x + (b.shape[1] - s.shape[1]) / 2, ty + (b.shape[0] - s.shape[0]) / 2, clamp(q))
            x += b.shape[1] + 18

def scene_outro(f, t):
    lt = t - S_OUTRO
    cx, cy = W / 2, H * (0.36 if PORTRAIT else 0.36)
    add(f, rays_sprite(-lt * 5, 0.35 * prog(lt, 0, 1.0), GOLD * 0.6 + ROSE * 0.4), cx - 950, cy - 950)
    e = prog(lt, 0, 0.9)
    sc = (1.6 - 0.6 * out_back(e, 1.2)) if e < 1 else 1.0
    sc *= 1 + 0.01 * math.sin(lt * 1.8)
    size = int(LOGO_SIZE * 0.85 * sc)
    spr = flower_sprite(size, [1] * 5) if abs(sc - 1) > 0.002 else cache_scaled(LOGO, 0.85)
    add(f, LOGO_GLOW, cx - LOGO_SIZE / 2 - LOGO_GLOW_PAD, cy - LOGO_SIZE / 2 - LOGO_GLOW_PAD, (0.5 + 0.2 * math.sin(lt * 2.2)) * prog(lt, 0.3, 1.0))
    blit(f, spr, cx - size / 2, cy - size / 2, prog(lt, 0, 0.3))
    by = cy + LOGO_SIZE * 0.85 / 2 + 40
    for k, h in enumerate(T['outro_h']):
        p = out_expo(prog(lt, 0.7 + k * 0.2, 1.4 + k * 0.2))
        center_blit(f, h, by, 1.0, p, (1 - p) * 28); by += h.shape[0] + 14
    p2 = prog(lt, 1.4, 2.0)
    if p2 > 0:
        ln = int(260 * out_expo(p2)); f[int(by) + 16:int(by) + 18, int(cx - ln / 2):int(cx + ln / 2)] += GOLD
        center_blit(f, T['outro_eb'], by + 36, p2, 1.0, (1 - out_cubic(p2)) * 12)
    fl = 1 - prog(lt, 0.0, 0.5)
    if fl > 0: f += (GOLD * 0.3 + WHITE * 0.3) * fl ** 2 * 0.5

SCENES = [(0.0, scene_intro), (S_SHOPS, scene_shops), (S_FOOD, scene_food), (S_FUN, scene_fun), (S_PARK, scene_park), (S_OUTRO, scene_outro)]

def scene_at(t):
    cur = SCENES[0][1]
    for start, fn in SCENES:
        if t >= start: cur = fn
    return cur

def wipe(f, t):
    """Zlatá linka a vínový pás, které zakryjí střih mezi scénami."""
    for c in CUTS:
        p = (t - (c - 0.28)) / 0.56
        if 0 <= p <= 1:
            if PORTRAIT:
                y = -800 + in_out(p) * (H + 1600)
                m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([(0, y), (W, y - 260), (W, y + 440), (0, y + 700)], fill=255)
                e = Image.new('L', (W, H), 0); de = ImageDraw.Draw(e)
                de.line([(0, y + 700), (W, y + 440)], fill=255, width=10); de.line([(0, y), (W, y - 260)], fill=255, width=10)
            else:
                x = -1300 + in_out(p) * (W + 2600)
                m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([(x, 0), (x + 1000, 0), (x + 1000 - 420, H), (x - 420, H)], fill=255)
                e = Image.new('L', (W, H), 0); de = ImageDraw.Draw(e)
                de.line([(x + 1000, 0), (x + 580, H)], fill=255, width=10); de.line([(x, 0), (x - 420, H)], fill=255, width=10)
            e = e.filter(ImageFilter.GaussianBlur(5))
            ma = np.asarray(m, np.float32)[..., None] / 255
            colr = WINE * (0.8 + 0.25 * (1 - ny[..., None] ** 2))
            f[:] = f * (1 - ma) + colr * ma
            f += np.asarray(e, np.float32)[..., None] / 255 * (GOLD * 0.9 + WHITE * 0.2)

def render(t):
    f = BG.copy()
    backdrop(f, t)
    scene_at(t)(f, t)
    wipe(f, t)
    fade = min(prog(t, 0, 0.7), 1 - prog(t, DURATION - 0.8, DURATION))
    f *= fade
    return np.clip(f * 255, 0, 255).astype(np.uint8)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if '--preview' in sys.argv:
        dest = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else Path('.')
        times = [float(x) for x in sys.argv[sys.argv.index('--preview') + 1:] if re.match(r'^[\d.]+$', x)]
        for t in times:
            Image.fromarray(render(t)).save(dest / f'preview-{NAME}-{t:05.1f}.png')
        print('previews:', dest); return
    frames = int(DURATION * FPS)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(OUT / f'{NAME}.mp4')]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    poster = None
    for k in range(frames):
        t = k / FPS
        fr = render(t)
        if abs(t - (S_OUTRO + 2.6)) < 0.5 / FPS: poster = fr
        proc.stdin.write(fr.tobytes())
        if k % 60 == 0: print(f'frame {k}/{frames}', flush=True)
    proc.stdin.close(); proc.wait()
    if poster is not None: Image.fromarray(poster).save(OUT / f'{NAME}-poster.jpg', quality=85)
    print('Done:', OUT / f'{NAME}.mp4')

if __name__ == '__main__':
    main()
