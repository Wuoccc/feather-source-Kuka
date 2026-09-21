import json,re,time,urllib.parse,urllib.request,concurrent.futures,difflib,threading
from pathlib import Path

APPS="apps.json"
OUT="apple_name_candidates.json"
SUMMARY="apple_name_summary.json"
UA="Mozilla/5.0"
lock=threading.Lock()

CJK_RE=re.compile(r"[\u3400-\u9fff]")
LATIN_RE=re.compile(r"[A-Za-z]")

SUFFIXES=[
"液态玻璃版","国服修改版","国服原版","国际版","多开版","多开","资源包","修改版",
"破解版","解锁版","付费版","内购版","增强版","Pro版","PRO版","VIP版","专业版",
"插件版","汉化版","直装版","去广告版","免广告版","无限版","最新版"
]

def get_json(url,retries=3):
    err=None
    for i in range(retries):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=15) as r:
                return json.loads(r.read().decode("utf-8","replace"))
        except Exception as e:
            err=e
            time.sleep(0.4*(i+1))
    return None

def search(term,country="cn",limit=25):
    qs=urllib.parse.urlencode({"term":term,"country":country,"entity":"software","limit":limit})
    return get_json("https://itunes.apple.com/search?"+qs) or {"results":[]}

def lookup(track_id,country):
    qs=urllib.parse.urlencode({"id":track_id,"country":country,"entity":"software"})
    return get_json("https://itunes.apple.com/lookup?"+qs) or {"results":[]}

def normalize(s):
    s=str(s or "").strip().lower()
    s=re.sub(r"\s+","",s)
    s=re.sub(r"[·•\-—–_:：()（）\[\]【】《》™®+,.，。!！?？'\"“”]","",s)
    return s

def cjk_only(s):
    return "".join(CJK_RE.findall(str(s or "")))

def strip_variant(name):
    s=str(name or "").strip()
    for suf in SUFFIXES:
        if s.endswith(suf) and len(s)>len(suf)+1:
            s=s[:-len(suf)].strip(" -—–_:：")
            break
    return s

def version_eq(a,b):
    a=str(a or "").strip().lower()
    b=str(b or "").strip().lower()
    if not a or not b:
        return False
    return a==b

def score_candidate(query,version,r):
    track=str(r.get("trackName") or "")
    qn=normalize(query); tn=normalize(track)
    qj=cjk_only(query); tj=cjk_only(track)
    score=0
    reasons=[]
    if qn and tn:
        if qn==tn:
            score+=100; reasons.append("exact_name")
        elif qn in tn or tn in qn:
            score+=75; reasons.append("name_contains")
    if qj and tj:
        if qj==tj:
            score+=90; reasons.append("exact_cjk")
        elif qj in tj or tj in qj:
            score+=65; reasons.append("cjk_contains")
        else:
            ratio=difflib.SequenceMatcher(None,qj,tj).ratio()
            if ratio>=0.8:
                score+=45; reasons.append(f"cjk_similarity:{ratio:.2f}")
    if version_eq(version,r.get("version")):
        score+=120; reasons.append("exact_version")
    return score,reasons

def extract_latin_title(track_name,original_cjk):
    s=str(track_name or "").strip()
    if not LATIN_RE.search(s):
        return None
    # If title already has both Chinese and Latin, prefer the clean Latin segment.
    parts=re.split(r"\s*[-—–|｜·:：]\s*|[（(][^）)]*[）)]",s)
    latin_parts=[]
    for p in parts:
        p=p.strip()
        if LATIN_RE.search(p) and not CJK_RE.search(p) and len(p)>=2:
            latin_parts.append(p)
    if latin_parts:
        latin_parts.sort(key=len,reverse=True)
        return latin_parts[0]
    if not CJK_RE.search(s):
        return s
    return None

def resolve_one(row):
    name=row["name"]
    ver=row.get("version")
    base=strip_variant(name)
    terms=[name]
    if base!=name:
        terms.append(base)
    results=[]
    seen=set()
    for term in terms:
        data=search(term,"cn",25)
        for r in data.get("results") or []:
            tid=r.get("trackId")
            if tid in seen: continue
            seen.add(tid)
            sc,why=score_candidate(base,ver,r)
            if sc>0:
                results.append((sc,why,r,term))
        time.sleep(0.03)
    if not results:
        return {"index":row["index"],"original":name,"version":ver,"status":"no_cn_match"}
    results.sort(key=lambda x:x[0],reverse=True)
    sc,why,best,term=results[0]
    if sc<90:
        return {"index":row["index"],"original":name,"version":ver,"status":"weak_cn_match","score":sc,
                "cnTrackName":best.get("trackName"),"cnVersion":best.get("version"),"trackId":best.get("trackId"),"reasons":why}
    english=extract_latin_title(best.get("trackName"),base)
    source="cn_trackName" if english else None
    # Lookup same track ID on international storefronts.
    if not english and best.get("trackId"):
        for country in ("vn","us","sg","hk","au","gb"):
            d=lookup(best["trackId"],country)
            rr=(d.get("results") or [])
            if rr:
                title=str(rr[0].get("trackName") or "").strip()
                if LATIN_RE.search(title) and not CJK_RE.search(title):
                    english=title; source=f"lookup_{country}"
                    break
            time.sleep(0.03)
    # Search international storefronts using Chinese/base term, useful if regional track IDs differ.
    if not english:
        for country in ("us","vn","sg","hk"):
            d=search(base,country,10)
            cand=[]
            for rr in d.get("results") or []:
                title=str(rr.get("trackName") or "")
                if not LATIN_RE.search(title) or CJK_RE.search(title):
                    continue
                bonus=0
                if version_eq(ver,rr.get("version")): bonus+=120
                # Compare seller with CN candidate when possible.
                seller_cn=normalize(best.get("sellerName") or best.get("artistName"))
                seller_int=normalize(rr.get("sellerName") or rr.get("artistName"))
                if seller_cn and seller_int and seller_cn==seller_int: bonus+=100
                if best.get("trackId")==rr.get("trackId"): bonus+=150
                if bonus:
                    cand.append((bonus,rr))
            if cand:
                cand.sort(key=lambda x:x[0],reverse=True)
                english=cand[0][1].get("trackName")
                source=f"search_{country}"
                break
            time.sleep(0.03)
    status="resolved" if english else "cn_match_no_english"
    return {
        "index":row["index"],"original":name,"version":ver,"base":base,"status":status,
        "score":sc,"reasons":why,"trackId":best.get("trackId"),"cnTrackName":best.get("trackName"),
        "cnVersion":best.get("version"),"sellerName":best.get("sellerName") or best.get("artistName"),
        "english":english,"englishSource":source
    }

with open(APPS,"r",encoding="utf-8") as f:
    data=json.load(f)

rows=[]
for i,a in enumerate(data.get("apps",[])):
    name=str(a.get("name",""))
    # only names that still START with CJK/symbol before a Latin international prefix
    first_nonspace=name.lstrip()[:1]
    if CJK_RE.search(first_nonspace or ""):
        rows.append({"index":i,"name":name,"version":a.get("version")})

out=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    futs=[ex.submit(resolve_one,r) for r in rows]
    for n,f in enumerate(concurrent.futures.as_completed(futs),1):
        try:
            out.append(f.result())
        except Exception as e:
            out.append({"status":"error","error":str(e)})
        if n%100==0:
            print("processed",n,flush=True)

out.sort(key=lambda x:x.get("index",10**9))
Path(OUT).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={}
for r in out:
    summary[r.get("status","unknown")]=summary.get(r.get("status","unknown"),0)+1
Path(SUMMARY).write_text(json.dumps({"total":len(out),"summary":summary},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"total":len(out),"summary":summary},ensure_ascii=False))
