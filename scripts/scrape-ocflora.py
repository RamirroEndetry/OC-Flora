import re, html, json, sys, urllib.request, concurrent.futures as cf
UA={'User-Agent':'Mozilla/5.0'}
def get(u):
    r=urllib.request.Request(u,headers=UA); return urllib.request.urlopen(r,timeout=40).read().decode('utf-8','replace')
def clean(t):
    t=re.sub(r'<br\s*/?>','\n',t); t=re.sub(r'</p>','\n',t); t=re.sub(r'<[^>]+>','',t); t=html.unescape(t)
    return re.sub(r'[ \t]+',' ',t).replace('\xa0',' ').strip()
def locs(sm): return re.findall(r'<loc>(.*?)</loc>',get(sm))
def parse_shop(u):
    s=get(u); m=re.search(r'<main.*?</main>',s,re.S); b=m.group(0) if m else s
    d={'url':u,'slug':u.rstrip('/').split('/')[-1]}
    d['name']=clean(re.search(r'<h1>(.*?)</h1>',b,re.S).group(1)) if re.search(r'<h1>',b) else ''
    lg=re.search(r'<div class="w-\[200px\][^>]*>\s*<img src="([^"]+)"',b); d['logo']=lg.group(1) if lg else ''
    hero=re.search(r'post-intro.*?<img[^>]+src="([^"]+)"',b,re.S); d['hero']=hero.group(1) if hero else ''
    desc=re.search(r'<h2>Základní informace</h2>(.*?)</div>',b,re.S); d['desc']=clean(desc.group(1)) if desc else ''
    for blk in re.findall(r'<div class="comp-data-table">(.*?)</div>\s*</div>\s*(?=<div class="comp-data-table">|</div>|<!--)',b,re.S):
        pass
    tables=re.findall(r'<div class="comp-data-table">\s*<div class="comp-data-table__left">(.*?)</div>\s*<div class="comp-data-table__right">(.*?)</div>\s*</div>',b,re.S)
    f={}
    for l,r in tables:
        k=clean(l).lower(); 
        if 'otev' in k:
            rows=re.findall(r'<div class="flex">\s*<p[^>]*>(.*?)</p>\s*<p[^>]*>(.*?)</p>',r,re.S)
            f['hours']=[[clean(a),clean(c)] for a,c in rows] or [[ '', clean(r)]]
        elif 'kategorie' in k: f['category']=clean(r)
        elif 'umíst' in k: f['floor']=clean(r)
        elif 'dárk' in k: f['giftcard']=clean(r)
        elif 'telefon' in k: f['phone']=clean(r)
        elif k=='web': 
            a=re.search(r'href="([^"]+)"',r); f['web']=a.group(1) if a else clean(r)
        elif 'mail' in k: f['email']=clean(r)
        elif 'facebook' in k: a=re.search(r'href="([^"]+)"',r); f['facebook']=a.group(1) if a else ''
        elif 'instagram' in k: a=re.search(r'href="([^"]+)"',r); f['instagram']=a.group(1) if a else ''
        else: f[k]=clean(r)
    d.update(f)
    e=re.search(r'entityId=(\d+)',b); d['entityId']=int(e.group(1)) if e else None
    fp=re.search(r'floorplanID=(\d+)',b); d['floorplanId']=int(fp.group(1)) if fp else None
    d['offers']=[{'url':a,'title':clean(t)} for a,t in re.findall(r'<a href="(https://www.ocflora.cz/nabidka/[^"]+)"[^>]*>.*?<p class="p--20 font-semibold">(.*?)</p>',b,re.S)]
    return d
def parse_post(u):
    s=get(u); m=re.search(r'<main.*?</main>',s,re.S); b=m.group(0) if m else s
    d={'url':u,'slug':u.rstrip('/').split('/')[-1]}
    d['title']=clean(re.search(r'<h1>(.*?)</h1>',b,re.S).group(1)) if '<h1>' in b else ''
    img=re.search(r'post-intro.*?(?:<img[^>]+src="([^"]+)"|background-image:\s*url\(([^)]+)\))',b,re.S)
    d['image']=(img.group(1) or img.group(2)).strip('\'"') if img else ''
    date=re.search(r'(\d{1,2}\.\s?\d{1,2}\.\s?\d{4})',clean(b)); d['date']=date.group(1) if date else ''
    shop=re.search(r'<p class="p--16 text-purple font-semibold">(.*?)</p>',b,re.S); d['shop']=clean(shop.group(1)) if shop else ''
    body=re.search(r'<section class="post-data">(.*?)</section>',b,re.S); d['body']=clean(body.group(1))[:3000] if body else clean(b)[:3000]
    d['links']=sorted(set(re.findall(r'href="(https?://(?!www\.ocflora\.cz)[^"]+)"',body.group(1) if body else b)))[:6]
    return d
if __name__=='__main__':
    out={}
    with cf.ThreadPoolExecutor(8) as ex:
        shops=locs('https://www.ocflora.cz/obchod-sitemap.xml'); print('shops',len(shops),file=sys.stderr)
        out['shops']=list(ex.map(parse_shop,shops))
        offers=locs('https://www.ocflora.cz/nabidka-sitemap.xml'); print('offers',len(offers),file=sys.stderr)
        out['offers']=list(ex.map(parse_post,offers))
        news=locs('https://www.ocflora.cz/aktualita-sitemap.xml'); print('news',len(news),file=sys.stderr)
        out['news']=list(ex.map(parse_post,news))
        out['categories']=locs('https://www.ocflora.cz/obchod-kategorie-sitemap.xml')
        out['pages']=locs('https://www.ocflora.cz/page-sitemap.xml')
    json.dump(out,open(sys.argv[1],'w',encoding='utf-8'),ensure_ascii=False,indent=1)
