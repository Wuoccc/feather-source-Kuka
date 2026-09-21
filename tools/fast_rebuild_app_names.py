import json,re,time,urllib.parse,urllib.request,concurrent.futures,threading
APPS="apps.json"; KUKA="https://app.ioskuka.com/appstore"; UA="Mozilla/5.0"
CJK=re.compile(r"[\u3400-\u9fff]"); LATIN=re.compile(r"[A-Za-z]")
VAR=["液态玻璃版","国服修改版","国服原版","国际版","多开版","多开","资源包","修改版","破解版","解锁版","付费版","内购版","增强版","插件版","汉化版","直装版","去广告版","免广告版","无限版"]
lock=threading.Lock(); cache={}
def js(url,retries=2):
    with lock:
        if url in cache:return cache[url]
    for i in range(retries):
        try:
            q=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(q,timeout=12) as r:d=json.loads(r.read().decode("utf-8","replace"))
            with lock:cache[url]=d
            return d
        except Exception: time.sleep(.25*(i+1))
    return None
def norm(s):
    return re.sub(r"[\s\-–—_:：·•!！?？'\"“”‘’()（）\[\]【】+]+","",str(s or "").lower())
def base(n):
    s=n.strip()
    for x in VAR:
        if s.endswith(x) and len(s)>len(x):return s[:-len(x)].strip(" -—–_:：")
    if s.lower().endswith("pro") and CJK.search(s[:-3]):return s[:-3].strip()
    return s
def search(term,country):
    u="https://itunes.apple.com/search?"+urllib.parse.urlencode({"term":term,"country":country,"entity":"software","limit":10})
    d=js(u);return d.get("results",[]) if isinstance(d,dict) else []
def lookup(i,country):
    u="https://itunes.apple.com/lookup?"+urllib.parse.urlencode({"id":i,"country":country,"entity":"software"})
    d=js(u);return d["results"][0] if isinstance(d,dict) and d.get("results") else None
def pick(orig,ver):
    b=base(orig); no=norm(orig); nb=norm(b); best=None
    for country in ("cn","vn"):
        for rank,c in enumerate(search(b,country)):
            tn=str(c.get("trackName") or ""); nt=norm(tn); sc=max(0,10-rank)
            if nt==no:sc+=130
            elif nt==nb:sc+=125
            elif len(nb)>=2 and (nb in nt or nt in nb):sc+=70
            if ver and str(c.get("version") or "").strip()==str(ver).strip():sc+=30
            z=(sc,-rank,c)
            if best is None or z[:2]>best[:2]:best=z
        if best and best[0]>=125:break
    if not best or best[0]<100:return None,None
    c=best[2]
    for country in ("vn","us","gb","sg","au"):
        r=lookup(c.get("trackId"),country)
        if r:
            n=str(r.get("trackName") or "").strip()
            if n and LATIN.search(n) and not CJK.search(n):return n,{"trackId":c.get("trackId"),"score":best[0],"store":country}
    return None,None
with open(APPS,encoding="utf-8") as f:d=json.load(f)
apps=d.get("apps") or []; live=js(KUKA)
if not live or not isinstance(live.get("apps"),list):raise SystemExit("Kuka live unavailable")
ka=[x for x in live["apps"] if str(x.get("name") or "").strip()!="‼️公告内容‼️"]
if len(ka)!=len(apps):raise SystemExit(f"count mismatch {len(ka)} {len(apps)}")
def one(i):
    o=str(ka[i].get("name") or "").strip()
    if not CJK.search(o):return i,o,"non",None
    en,meta=pick(o,apps[i].get("version"))
    if en:return i,f"{en} ({o})","apple",meta
    return i,o,"original",None
res=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
    for x in ex.map(one,range(len(apps))):res.append(x)
cnt={"apple":0,"original":0,"non":0}; samples=[]
for i,n,s,m in res:
    apps[i]["name"]=n;cnt[s]+=1
    if s=="apple" and len(samples)<150:samples.append({"index":i,"name":n,**m})
with open(APPS,"w",encoding="utf-8") as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write("\n")
out={"apps":len(apps),"appleResolved":cnt["apple"],"keptOriginalKuka":cnt["original"],"nonCjk":cnt["non"],"sampleResolved":samples}
with open(".name-normalization-summary-fast.json","w",encoding="utf-8") as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write("\n")
print(json.dumps(out,ensure_ascii=False,indent=2))
