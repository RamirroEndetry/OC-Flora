# -*- coding: utf-8 -*-
"""Z originálního loga (assets/OC Flora - Logo/logo-oc-flora.png) vyrobí ikony aplikace a bílé varianty pro záhlaví.
Usage: python -X utf8 scripts/make-icons.py
"""
import base64, io
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'assets' / 'OC Flora - Logo' / 'logo-oc-flora.png'
WINE = (108, 29, 69)

im = Image.open(SRC).convert('RGBA')
a = np.asarray(im.getchannel('A'))
cols = np.where(a.max(axis=0) > 20)[0]
gaps = np.diff(cols); i = int(gaps.argmax()); split = int((cols[i] + cols[i + 1]) // 2)
mark = im.crop((0, 0, split, im.height)); mark = mark.crop(mark.getbbox())
word = im.crop((split, 0, im.width, im.height)); word = word.crop(word.getbbox())

def recolor(img, rgb):
    out = Image.new('RGBA', img.size, rgb + (255,)); out.putalpha(img.getchannel('A')); return out

def fit(img, w=None, h=None):
    if w: h = round(img.height * w / img.width)
    else: w = round(img.width * h / img.height)
    return img.resize((w, h), Image.LANCZOS)

# bílé varianty pro záhlaví aplikace
fit(recolor(mark, (255, 255, 255)), h=256).save(ROOT / 'assets' / 'logo-mark-white.png', optimize=True)
fit(recolor(word, (255, 255, 255)), w=640).save(ROOT / 'assets' / 'logo-flora-white.png', optimize=True)
# vínová varianta (světlé pozadí, např. tisk)
fit(recolor(mark, WINE), h=256).save(ROOT / 'assets' / 'logo-mark-wine.png', optimize=True)

def icon(size, maskable=False):
    S = size * 2
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if maskable: d.rectangle([0, 0, S, S], fill=WINE)
    else: d.rounded_rectangle([0, 0, S - 1, S - 1], radius=S * 28 // 128, fill=WINE)
    m = fit(recolor(mark, (255, 255, 255)), h=int(S * (0.5 if maskable else 0.62)))
    img.alpha_composite(m, ((S - m.width) // 2, (S - m.height) // 2))
    return img.resize((size, size), Image.LANCZOS)

icon(192).save(ROOT / 'assets' / 'icon-192.png', optimize=True)
icon(512).save(ROOT / 'assets' / 'icon-512.png', optimize=True)
icon(512, True).save(ROOT / 'assets' / 'icon-maskable-512.png', optimize=True)
# SVG ikona: vínový zaoblený čtverec s vloženým bílým znakem
buf = io.BytesIO(); fit(recolor(mark, (255, 255, 255)), h=160).save(buf, 'PNG', optimize=True)
mw = fit(recolor(mark, (255, 255, 255)), h=160).width
b64 = base64.b64encode(buf.getvalue()).decode()
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="56" fill="#6c1d45"/>
  <image x="{(256 - mw) / 2:.1f}" y="48" width="{mw}" height="160" xlink:href="data:image/png;base64,{b64}"/>
</svg>
'''
(ROOT / 'assets' / 'icon.svg').write_text(svg, encoding='utf-8')
print('icons ok, mark', mark.size, 'word', word.size)
