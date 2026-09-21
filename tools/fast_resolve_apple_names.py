import json,re,time,urllib.parse,urllib.request,concurrent.futures
from pathlib import Path
APPS="apps.json"; OUT="fast_apple_candidates.json"; UA="Mozilla/5.0"
CJK=re.compile(r"[\u3400-\u9fff]"); LAT=re.compile(r"[A-Za-z]")
SUFFIXES=["液态玻璃版","国服修改版","国服原版","国际版","多开版","多开","资源包","修改版","破解版","解锁版","付费版","内购版","增强版","插件版","汉化版","直装版","去广告版","免广告版","无限版","最新版"]
def jget(url):
    for n in range(2):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=8) as r:
                return json.loads(r.read().decode("utf-8","replace"))
        except Exception:
            time.sleep(.15*(n+1))
    return {}
def search(term,country="cn",limit=15):
    q=urllib.parse.urlencode({"term":term,"country":country,"entity":"software","limit":limit})
    return jget("https://itunes.apple.com/search?"+q).get("results",[])
def lookup(tid,country):
    q=urllib.parse.urlencode({"id":tid,"country":country,"entity":"software"})
    return jget("https://itunes.apple.com/lookup?"+q).get("results",[])
def stripv(s):
    s=s.strip()
    for x in SUFFIXES:
        if s.endswith(x) and len(s)>len(x):
            return s[:-len(x)].strip(" -—–_:：")
    if s.lower().endswith("pro") and CJK.search(s[:-3]): return s[:-3].strip()
    return s
def cj(s): return "".join(CJK.findall(str(s or "")))
def norm(s): return re.sub(r"[\s\-—–_:：()（）\[\]【】《》™®+,.，。!！?？'\"“”·•]","",str(s or "").lower())
def vmatch(a,b): return bool(a and b and str(a).strip().lower()==str(b).strip().lower())
def english_from_title(s):
    s=str(s or "").strip()
    if not LAT.search(s): return None
    if not CJK.search(s): return s
    parts=re.split(r"\s*[-—–|｜:：]\s*",s)
    good=[p.strip() for p in parts if LAT.search(p) and not CJK.search(p)]
    if good:return max(good,key=len)
    m=re.findall(r"[A-Za-z][A-Za-z0-9'&+.!: -]{2,}",s)
    return max([x.strip() for x in m],key=len) if m else None
def one(row):
    i,name,ver=row; base=stripv(name)
    rs=search(base,"cn",15)
    scored=[]
    qj=cj(base); qn=norm(base)
    for r in rs:
        tn=str(r.get("trackName") or ""); tj=cj(tn); score=0; why=[]
        if qn and norm(tn)==qn: score+=100; why.append("exact_name")
        elif qj and tj and (qj==tj): score+=90; why.append("exact_cjk")
        elif qj and tj and (qj in tj or tj in qj): score+=60; why.append("cjk_contains")
        if vmatch(ver,r.get("version")): score+=120; why.append("exact_version")
        if score: scored.append((score,why,r))
    if not scored:return {"index":i,"original":name,"version":ver,"status":"no_match"}
    scored.sort(key=lambda x:x[0],reverse=True); score,why,best=scored[0]
    if score<90:return {"index":i,"original":name,"version":ver,"status":"weak","score":score,"cnTrackName":best.get("trackName")}
    en=english_from_title(best.get("trackName")); src="cn_title" if en else None
    if not en and best.get("trackId"):
        for country in ("vn","us","sg","hk"):
            rr=lookup(best["trackId"],country)
            if rr:
                t=str(rr[0].get("trackName") or "").strip()
                if LAT.search(t) and not CJK.search(t):
                    en=t; src="lookup_"+country; break
    return {"index":i,"original":name,"version":ver,"base":base,"status":"resolved" if en else "matched_no_english",
            "score":score,"reasons":why,"trackId":best.get("trackId"),"cnTrackName":best.get("trackName"),
            "cnVersion":best.get("version"),"sellerName":best.get("sellerName") or best.get("artistName"),
            "english":en,"englishSource":src}
with open(APPS,"r",encoding="utf-8") as f:d=json.load(f)
rows=[]
for i,a in enumerate(d.get("apps",[])):
    n=str(a.get("name",""))
    if CJK.search(n.lstrip()[:1] or ""): rows.append((i,n,a.get("version")))
out=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
    for r in ex.map(one,rows): out.append(r)
Path(OUT).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"total":len(out),"resolved":sum(x.get("status")=="resolved" for x in out),"matched_no_english":sum(x.get("status")=="matched_no_english" for x in out),"no_match":sum(x.get("status")=="no_match" for x in out),"weak":sum(x.get("status")=="weak" for x in out)},ensure_ascii=False))
