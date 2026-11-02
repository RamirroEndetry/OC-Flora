import json, urllib.request, concurrent.futures as cf, os, sys
raw=json.load(open(sys.argv[1],encoding='utf-8'))
os.makedirs('assets/logos',exist_ok=True)
def dl(s):
    try:
        r=urllib.request.Request(s['logo'],headers={'User-Agent':'Mozilla/5.0'}); b=urllib.request.urlopen(r,timeout=30).read()
        open('assets/logos/%s.svg'%s['slug'],'wb').write(b); return len(b)
    except Exception as e: return 'ERR '+str(e)
with cf.ThreadPoolExecutor(8) as ex: res=list(ex.map(dl,raw['shops']))
print('ok',sum(1 for r in res if isinstance(r,int)),'err',[(s['slug'],r) for s,r in zip(raw['shops'],res) if not isinstance(r,int)],'total KB',sum(r for r in res if isinstance(r,int))//1024)
