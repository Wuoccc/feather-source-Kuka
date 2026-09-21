import json,re,time,urllib.parse,urllib.request,concurrent.futures,hashlib,io,os
from PIL import Image

APPS="apps.json"
KUKA_URL="https://app.ioskuka.com/appstore"
UA="Mozilla/5.0"
CJK=re.compile(r"[\u3400-\u9fff]")
LATIN=re.compile(r"[A-Za-z]")
VARIANTS=[
"液态玻璃版","国服修改版","国服原版","国际版","多开版","多开","资源包","修改版","破解版",
"解锁版","付费版","内购版","增强版","插件版","汉化版","直装版","去广告版","免广告版","无限版"
]

def get_json(url,retries=3):
    for i in range(retries):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=20) as r:
                return json.loads(r.read().decode("utf-8","replace"))
        except Exception:
            time.sleep(.4*(i+1))
    return None

def get_bytes(url,retries=2):
    if not url: return None
    if url.startswith("http://"): url="https://"+url[7:]
    for i in range(retries):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=15) as r:
                return r.read()
        except Exception:
            time.sleep(.25*(i+1))
    return None

def norm(s):
    s=str(s or "").lower()
    s=re.sub(r"[\s\-–—_:：·•!！?？'\"“”‘’()（）\[\]【】+]+","",s)
    return s

def split_base(name):
    s=str(name or "").strip()
    for x in VARIANTS:
        if s.endswith(x) and len(s)>len(x):
            return s[:-len(x)].strip(" -—–_:：")
    if s.lower().endswith("pro") and CJK.search(s[:-3]):
        return s[:-3].strip()
    return s

def ahash(data):
    try:
        im=Image.open(io.BytesIO(data)).convert("L").resize((8,8))
        pix=list(im.getdata()); avg=sum(pix)/64.0
        return sum((1<<i) for i,v in enumerate(pix) if v>=avg)
    except Exception:
        return None

def ham(a,b):
    if a is None or b is None: return 99
    return (a^b).bit_count()

def search(term,country):
    qs=urllib.parse.urlencode({"term":term,"country":country,"entity":"software","limit":12})
    d=get_json("https://itunes.apple.com/search?"+qs)
    return d.get("results",[]) if isinstance(d,dict) else []

def lookup(track_id,country):
    qs=urllib.parse.urlencode({"id":track_id,"country":country,"entity":"software"})
    d=get_json("https://itunes.apple.com/lookup?"+qs)
    if isinstance(d,dict) and d.get("results"): return d["results"][0]
    return None

def candidate_score(c,original,base,kver,khash,rank):
    tn=str(c.get("trackName") or "")
    ntn=norm(tn); no=norm(original); nb=norm(base)
    score=max(0,12-rank)
    if ntn==no: score+=120
    elif ntn==nb: score+=115
    elif nb and len(nb)>=2 and (nb in ntn or ntn in nb): score+=55
    if kver and str(c.get("version") or "").strip()==str(kver).strip(): score+=28
    dist=99
    art=c.get("artworkUrl100") or c.get("artworkUrl512")
    if art and khash is not None:
        dist=ham(khash,ahash(get_bytes(art)))
        if dist<=6: score+=85
        elif dist<=10: score+=65
        elif dist<=14: score+=40
    return score,dist

def english_name(track_id):
    for country in ("vn","us","gb","au","sg"):
        r=lookup(track_id,country)
        if not r: continue
        name=str(r.get("trackName") or "").strip()
        if name and LATIN.search(name) and not CJK.search(name):
            return name,country,r
    return None,None,None

def resolve_one(args):
    idx,orig,app=args
    if not CJK.search(orig):
        return idx,orig,"non_cjk",None
    base=split_base(orig)
    kver=app.get("version")
    khash=ahash(get_bytes(app.get("iconURL")))
    best=None
    seen=set()
    terms=[base]
    if orig!=base: terms.append(orig)
    for country in ("cn","vn"):
        for term in terms:
            key=(country,term)
            if key in seen: continue
            seen.add(key)
            rs=search(term,country)
            for rank,c in enumerate(rs):
                sc,dist=candidate_score(c,orig,base,kver,khash,rank)
                rec=(sc,-dist,country,rank,c)
                if best is None or rec[:2]>best[:2]: best=rec
            if best and best[0]>=150:
                break
        if best and best[0]>=150:
            break
    if not best:
        return idx,orig,"unresolved",None
    score,negdist,country,rank,c=best
    dist=-negdist
    strong = score>=115 or (score>=90 and dist<=14) or (score>=75 and dist<=8)
    if not strong:
        return idx,orig,"unresolved",{"score":score,"iconDistance":dist,"candidate":c.get("trackName"),"trackId":c.get("trackId")}
    en,store,lr=english_name(c.get("trackId"))
    if not en:
        return idx,orig,"unresolved",{"score":score,"iconDistance":dist,"candidate":c.get("trackName"),"trackId":c.get("trackId")}
    new=f"{en} ({orig})"
    return idx,new,"apple",{"score":score,"iconDistance":dist,"trackId":c.get("trackId"),"store":store,"official":en,"original":orig}

with open(APPS,"r",encoding="utf-8") as f:
    data=json.load(f)
apps=data.get("apps") or []
live=get_json(KUKA_URL)
if not live or not isinstance(live.get("apps"),list):
    raise SystemExit("Cannot fetch live Kuka")
live_apps=[a for a in live["apps"] if str(a.get("name") or "").strip()!="‼️公告内容‼️"]
if len(live_apps)!=len(apps):
    raise SystemExit(f"Catalog mismatch live={len(live_apps)} current={len(apps)}")

jobs=[(i,str(live_apps[i].get("name") or "").strip(),apps[i]) for i in range(len(apps))]
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for r in ex.map(resolve_one,jobs):
        results.append(r)

resolved=unresolved=non_cjk=0
details=[]
for idx,new,status,meta in results:
    if status=="apple":
        apps[idx]["name"]=new; resolved+=1
        if len(details)<250: details.append({"index":idx,"name":new,**(meta or {})})
    elif status=="unresolved":
        # Critical rule: keep exact Kuka name when official English name is not verified.
        apps[idx]["name"]=str(live_apps[idx].get("name") or "").strip()
        unresolved+=1
    else:
        # For non-CJK entries, keep the live Kuka name to avoid stale/manual aliases.
        apps[idx]["name"]=str(live_apps[idx].get("name") or apps[idx].get("name") or "").strip()
        non_cjk+=1

with open(APPS,"w",encoding="utf-8") as f:
    json.dump(data,f,ensure_ascii=False,indent=2); f.write("\n")

summary={
 "apps":len(apps),
 "cjk":resolved+unresolved,
 "appleResolved":resolved,
 "keptOriginalKuka":unresolved,
 "nonCjk":non_cjk,
 "sampleResolved":details[:120]
}
with open(".name-normalization-summary.json","w",encoding="utf-8") as f:
    json.dump(summary,f,ensure_ascii=False,indent=2); f.write("\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
