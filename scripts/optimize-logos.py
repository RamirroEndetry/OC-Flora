"""SVG loga s vlozenym rastrem (PNG/JPEG v base64) prevede na male PNG, aby aplikace nenacitala megabajty.
Usage: python -X utf8 scripts/optimize-logos.py
"""
import re, base64, io, glob, os
from PIL import Image
MAX_W = 560
done = 0
for f in sorted(glob.glob('assets/logos/*.svg')):
    if os.path.getsize(f) < 120_000:
        continue
    t = open(f, encoding='utf-8', errors='replace').read()
    m = re.search(r'data:image/(png|jpeg|jpg);base64,([A-Za-z0-9+/=\s]+)', t)
    if not m:
        print('skip (no raster)', f); continue
    img = Image.open(io.BytesIO(base64.b64decode(re.sub(r'\s', '', m.group(2))))).convert('RGBA')
    # orez pruhledneho / bileho okraje
    bg = Image.new('RGBA', img.size, (255, 255, 255, 0))
    alpha = img.getchannel('A')
    bbox = alpha.getbbox()
    if bbox and alpha.getextrema()[0] < 255:
        img = img.crop(bbox)
    else:
        rgb = img.convert('RGB'); from PIL import ImageChops
        diff = ImageChops.difference(rgb, Image.new('RGB', rgb.size, (255, 255, 255)))
        bbox = diff.point(lambda p: 255 if p > 12 else 0).getbbox()
        if bbox: img = img.crop(bbox)
    if img.width > MAX_W:
        img = img.resize((MAX_W, max(1, round(img.height * MAX_W / img.width))), Image.LANCZOS)
    out = f[:-4] + '.png'
    img.save(out, optimize=True)
    os.remove(f)
    done += 1
    print('ok', out, os.path.getsize(out) // 1024, 'KB')
print('converted', done)
