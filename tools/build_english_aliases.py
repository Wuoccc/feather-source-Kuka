import json,re,time,urllib.parse,urllib.request
from pathlib import Path
APPS="apps.json"
OUT="translated_name_aliases.json"
UA="Mozilla/5.0"
CJK=re.compile(r"[\u3400-\u9fff]")
VARIANTS=[
("液态玻璃版","Liquid Glass Edition"),("国服修改版","CN Mod"),("国服原版","CN Original"),
("国际版","International"),("多开版","Multi-Instance"),("多开","Multi-Instance"),
("资源包","Resource Pack"),("修改版","Mod"),("破解版","Mod"),("解锁版","Unlocked"),
("付费版","Paid Edition"),("内购版","IAP Edition"),("增强版","Enhanced"),
("插件版","Plugin Edition"),("汉化版","Chinese-localized"),("直装版","Direct Install"),
("去广告版","Ad-Free"),("免广告版","Ad-Free"),("无限版","Unlimited Edition")
]
CURATED={
"梦想城镇":"Township","潜水员戴夫":"DAVE THE DIVER","模拟人生":"The Sims FreePlay",
"地球末日:生存":"Last Day on Earth: Survival","地球末日：生存":"Last Day on Earth: Survival",
"饥饿鲨：世界":"Hungry Shark World","饥饿鲨:世界":"Hungry Shark World",
"我的世界":"Minecraft","房产达人":"House Flipper","饥荒联机版":"Don't Starve Together",
"欧洲卡车模拟器3":"Truckers of Europe 3","植物大战僵尸杂交版":"Plants vs. Zombies Hybrid Edition",
"红警2":"Command & Conquer: Red Alert 2","开心消消乐":"Anipop","行尸走肉":"The Walking Dead",
"白猫Project":"White Cat Project","萌龙大乱斗":"Dragon Mania Legends","掘地求升+":"Getting Over It+",
"狐猴浏览器":"Lemur Browser","抖音":"Douyin","王者荣耀":"Honor of Kings","原神":"Genshin Impact",
"崩坏3":"Honkai Impact 3rd","明日方舟":"Arknights","第五人格":"Identity V","蛋仔派对":"Eggy Party",
"鸣潮":"Wuthering Waves","绝区零":"Zenless Zone Zero","恋与深空":"Love and Deepspace",
"光遇":"Sky: Children of the Light","光·遇":"Sky: Children of the Light"
}
def split_variant(s):
    s=s.strip()
    for zh,en in VARIANTS:
        if s.endswith(zh) and len(s)>len(zh):
            return s[:-len(zh)].strip(" -—–_:："),en
    if s.lower().endswith("pro") and CJK.search(s[:-3]):
        return s[:-3].strip(),"Pro"
    return s,None
def translate_batch(items):
    if not items:return {}
    marker="\n<<<KUKA_SEP>>>\n"
    text=marker.join(items)
    qs=urllib.parse.urlencode({"client":"gtx","sl":"zh-CN","tl":"en","dt":"t","q":text})
    url="https://translate.googleapis.com/translate_a/single?"+qs
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    with urllib.request.urlopen(req,timeout=30) as r:
        data=json.loads(r.read().decode("utf-8","replace"))
    out="".join(x[0] for x in data[0] if isinstance(x,list) and x and isinstance(x[0],str))
    parts=out.split("<<<KUKA_SEP>>>")
    parts=[p.strip(" \n-—–") for p in parts]
    if len(parts)!=len(items):
        return {}
    return dict(zip(items,parts))
with open(APPS,"r",encoding="utf-8") as f:d=json.load(f)
targets={}
for i,a in enumerate(d.get("apps",[])):
    name=str(a.get("name",""))
    if CJK.search(name.lstrip()[:1] or ""):
        base,var=split_variant(name)
        targets.setdefault(base,[]).append({"index":i,"original":name,"variant":var})
aliases={}
missing=[x for x in targets if x not in CURATED]
for base,en in CURATED.items():
    if base in targets: aliases[base]={"english":en,"source":"curated"}
for k in range(0,len(missing),20):
    batch=missing[k:k+20]
    try:
        got=translate_batch(batch)
    except Exception:
        got={}
    for base in batch:
        en=(got.get(base) or "").strip()
        if en and not CJK.search(en):
            aliases[base]={"english":en,"source":"translation"}
    time.sleep(0.08)
Path(OUT).write_text(json.dumps({"aliases":aliases,"targets":targets},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"unique_bases":len(targets),"aliases":len(aliases),"unresolved":len(targets)-len(aliases)},ensure_ascii=False))
