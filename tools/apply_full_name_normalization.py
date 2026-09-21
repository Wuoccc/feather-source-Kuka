import json,re,time,urllib.parse,urllib.request,concurrent.futures,threading
from pathlib import Path

APPS="apps.json"
CAND="apple_name_candidates.json"
REPORT="name_normalization_report.json"
UA="Mozilla/5.0"
CJK_RE=re.compile(r"[\u3400-\u9fff]")
LATIN_RE=re.compile(r"[A-Za-z]")

VARIANTS=[
("液态玻璃版","Liquid Glass Edition"),
("国服修改版","CN Mod"),
("国服原版","CN Original"),
("国际版","International"),
("多开版","Multi-Instance"),
("多开","Multi-Instance"),
("资源包","Resource Pack"),
("修改版","Mod"),
("破解版","Mod"),
("解锁版","Unlocked"),
("付费版","Paid Edition"),
("内购版","IAP Edition"),
("增强版","Enhanced"),
("插件版","Plugin Edition"),
("汉化版","Chinese-localized"),
("直装版","Direct Install"),
("去广告版","Ad-Free"),
("免广告版","Ad-Free"),
("无限版","Unlimited Edition"),
]

# Curated aliases for well-known products where the international name is established.
CURATED={
"梦想城镇":"Township",
"潜水员戴夫":"DAVE THE DIVER",
"模拟人生":"The Sims FreePlay",
"地球末日:生存":"Last Day on Earth: Survival",
"地球末日：生存":"Last Day on Earth: Survival",
"饥饿鲨：世界":"Hungry Shark World",
"饥饿鲨:世界":"Hungry Shark World",
"我的世界":"Minecraft",
"房产达人":"House Flipper",
"饥荒联机版":"Don't Starve Together",
"欧洲卡车模拟器3":"Truckers of Europe 3",
"植物大战僵尸杂交版":"Plants vs. Zombies Hybrid Edition",
"红警2":"Command & Conquer: Red Alert 2",
"红警2资源包":"Command & Conquer: Red Alert 2 Resource Pack",
"开心消消乐":"Anipop",
"行尸走肉":"The Walking Dead",
"白猫Project":"White Cat Project",
"萌龙大乱斗":"Dragon Mania Legends",
"掘地求升+":"Getting Over It+",
"传说对决  Arena of Valor":"Arena of Valor",
"狐猴浏览器":"Lemur Browser",
}

def http_json(url,retries=3):
    for i in range(retries):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=15) as r:
                return json.loads(r.read().decode("utf-8","replace"))
        except Exception:
            time.sleep(0.5*(i+1))
    return None

def gtranslate(text):
    if not text or not CJK_RE.search(text):
        return text
    qs=urllib.parse.urlencode({
        "client":"gtx","sl":"zh-CN","tl":"en","dt":"t","q":text
    })
    data=http_json("https://translate.googleapis.com/translate_a/single?"+qs)
    if isinstance(data,list) and data and isinstance(data[0],list):
        parts=[]
        for x in data[0]:
            if isinstance(x,list) and x and isinstance(x[0],str):
                parts.append(x[0])
        s="".join(parts).strip()
        if s:
            return s
    return None

def split_variant(name):
    s=name.strip()
    for zh,en in VARIANTS:
        if s.endswith(zh) and len(s)>len(zh):
            return s[:-len(zh)].strip(" -—–_:："),en
    # Pro can be appended to Chinese base
    if s.lower().endswith("pro") and CJK_RE.search(s[:-3]):
        return s[:-3].strip(),"Pro"
    return s,None

def clean_en(s):
    s=str(s or "").strip()
    s=re.sub(r"\s+"," ",s)
    s=s.strip(" -—–_:：()（）[]【】")
    return s

with open(APPS,"r",encoding="utf-8") as f:
    data=json.load(f)
with open(CAND,"r",encoding="utf-8") as f:
    cand=json.load(f)

by_index={r.get("index"):r for r in cand if isinstance(r,dict) and isinstance(r.get("index"),int)}

targets=[]
for i,a in enumerate(data.get("apps",[])):
    name=str(a.get("name",""))
    first=name.lstrip()[:1]
    if CJK_RE.search(first or ""):
        base,var=split_variant(name)
        targets.append((i,name,base,var))

# Translate only unique bases not already curated and not safely Apple-resolved.
bases=set()
for i,name,base,var in targets:
    r=by_index.get(i,{})
    apple_ok=(r.get("status")=="resolved" and r.get("english") and (
        (r.get("score") or 0)>=180 or str(r.get("englishSource") or "").startswith("lookup_")
    ))
    if not apple_ok and base not in CURATED:
        bases.add(base)

translations={}
def tr_one(x):
    return x,gtranslate(x)

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for base,en in ex.map(tr_one,sorted(bases)):
        translations[base]=en
        time.sleep(0.01)

report=[]
for i,original,base,var in targets:
    r=by_index.get(i,{})
    english=None
    source=None
    apple_ok=(r.get("status")=="resolved" and r.get("english") and (
        (r.get("score") or 0)>=180 or str(r.get("englishSource") or "").startswith("lookup_")
    ))
    if apple_ok:
        english=clean_en(r.get("english"))
        source="apple"
    elif base in CURATED:
        english=CURATED[base]
        source="curated"
    else:
        english=clean_en(translations.get(base))
        source="translation"
    if not english or CJK_RE.search(english):
        # Last resort roman-readable marker; keep source name intact if translation failed.
        continue
    if var and var.lower() not in english.lower():
        english=f"{english} - {var}"
    new=f"{english} ({original})"
    data["apps"][i]["name"]=new
    report.append({"index":i,"original":original,"new":new,"source":source,
                   "appleScore":r.get("score"),"appleSource":r.get("englishSource")})

with open(APPS,"w",encoding="utf-8") as f:
    json.dump(data,f,ensure_ascii=False,indent=2)
    f.write("\n")
Path(REPORT).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({
    "targets":len(targets),
    "changed":len(report),
    "apple":sum(1 for x in report if x["source"]=="apple"),
    "curated":sum(1 for x in report if x["source"]=="curated"),
    "translation":sum(1 for x in report if x["source"]=="translation"),
    "remaining":len(targets)-len(report)
},ensure_ascii=False))
