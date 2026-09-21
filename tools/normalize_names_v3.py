import concurrent.futures
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

APPS_PATH = Path("apps.json")
REPORT_PATH = Path(".name-normalization-v3-report.json")
KUKA_URL = "https://app.ioskuka.com/appstore"
UA = "Mozilla/5.0 (Kuka Feather Name Normalizer/3.0)"

CJK = re.compile(r"[\u3400-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")

VARIANTS = [
    ("液态玻璃版", "Liquid Glass Edition"),
    ("国服修改版", "CN Mod"),
    ("国服原版", "CN Original"),
    ("国际服", "International"),
    ("国际版", "International"),
    ("多开版本", "Multi-Instance"),
    ("多开版", "Multi-Instance"),
    ("多开", "Multi-Instance"),
    ("资源包", "Resource Pack"),
    ("修改版", "Mod"),
    ("破解版", "Mod"),
    ("解锁版", "Unlocked"),
    ("付费版", "Paid Edition"),
    ("内购版", "IAP Edition"),
    ("增强版", "Enhanced"),
    ("插件版", "Plugin Edition"),
    ("汉化版", "Chinese-localized"),
    ("直装版", "Direct Install"),
    ("去广告版", "Ad-Free"),
    ("免广告版", "Ad-Free"),
    ("无限版", "Unlimited Edition"),
    ("企业版", "Enterprise Edition"),
]

CURATED = {
    "无他相机": "Wuta Camera - Nice Shot Always",
    "元气骑士": "Soul Knight",
    "梦想城镇": "Township",
    "潜水员戴夫": "DAVE THE DIVER",
    "模拟人生": "The Sims FreePlay",
    "地球末日:生存": "Last Day on Earth: Survival",
    "地球末日：生存": "Last Day on Earth: Survival",
    "饥饿鲨：世界": "Hungry Shark World",
    "饥饿鲨:世界": "Hungry Shark World",
    "我的世界": "Minecraft",
    "房产达人": "House Flipper",
    "饥荒联机版": "Don't Starve Together",
    "欧洲卡车模拟器3": "Truckers of Europe 3",
    "植物大战僵尸杂交版": "Plants vs. Zombies Hybrid Edition",
    "红警2": "Command & Conquer: Red Alert 2",
    "开心消消乐": "Anipop",
    "行尸走肉": "The Walking Dead",
    "白猫Project": "White Cat Project",
    "萌龙大乱斗": "Dragon Mania Legends",
    "掘地求升+": "Getting Over It+",
    "传说对决  Arena of Valor": "Arena of Valor",
    "狐猴浏览器": "Lemur Browser",
    "小红书": "rednote",
    "微信": "WeChat",
    "多邻国": "Duolingo",
    "支付宝": "Alipay",
    "企业微信": "WeCom",
    "网易云音乐": "NetEase Cloud Music",
    "酷狗音乐": "KuGou Music",
    "酷我音乐": "Kuwo Music",
    "百度网盘": "Baidu Netdisk",
    "哔哩哔哩": "bilibili",
    "QQ音乐": "QQ Music",
    "微博": "Weibo",
    "知乎": "Zhihu",
    "淘宝": "Taobao",
    "京东": "JD.com",
    "拼多多": "Pinduoduo",
    "美团": "Meituan",
    "饿了么": "Ele.me",
    "高德地图": "Amap",
    "百度地图": "Baidu Maps",
    "百度贴吧": "Baidu Tieba",
    "钉钉": "DingTalk",
    "飞书": "Feishu",
    "今日头条": "Toutiao",
    "快手": "Kuaishou",
    "优酷": "YOUKU",
    "爱奇艺": "iQIYI",
    "喜马拉雅": "Ximalaya",
    "豆瓣": "Douban",
    "百度": "Baidu",
    "UC浏览器": "UC Browser",
    "夸克浏览器": "Quark Browser",
    "夸克": "Quark",
    "王者荣耀": "Honor of Kings",
    "原神": "Genshin Impact",
    "崩坏：星穹铁道": "Honkai: Star Rail",
    "崩坏:星穹铁道": "Honkai: Star Rail",
    "崩坏3": "Honkai Impact 3rd",
    "明日方舟": "Arknights",
    "第五人格": "Identity V",
    "蛋仔派对": "Eggy Party",
    "鸣潮": "Wuthering Waves",
    "绝区零": "Zenless Zone Zero",
    "恋与深空": "Love and Deepspace",
    "光·遇": "Sky: Children of the Light",
    "光遇": "Sky: Children of the Light",
    "抖音": "Douyin",
    "美颜相机": "BeautyCam",
    "美图秀秀": "Meitu",
    "彩云天气": "Caiyun Weather",
}

def http_json(url, retries=2, timeout=8):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            time.sleep(0.2 * (i + 1))
    return {}

def search_cn(term):
    q = urllib.parse.urlencode({"term": term, "country": "cn", "entity": "software", "limit": 25})
    d = http_json("https://itunes.apple.com/search?" + q)
    return d.get("results", []) if isinstance(d, dict) else []

def batch_lookup(ids, country):
    if not ids:
        return {}
    q = urllib.parse.urlencode({"id": ",".join(str(x) for x in ids), "country": country, "entity": "software"})
    d = http_json("https://itunes.apple.com/lookup?" + q)
    out = {}
    if isinstance(d, dict):
        for r in d.get("results", []) or []:
            tid = r.get("trackId")
            if tid is not None:
                out[int(tid)] = r
    return out

def norm(s):
    return re.sub(r"[\s\-—–_:：()（）\[\]【】《》™®+,.，。!！?？'\"“”·•/|｜]", "", str(s or "").lower())

def cj(s):
    return "".join(CJK.findall(str(s or "")))

def split_variant(name):
    s = str(name or "").strip()
    for zh, en in VARIANTS:
        if s.endswith(zh) and len(s) > len(zh):
            return s[:-len(zh)].strip(" -—–_:："), en
    if s.lower().endswith("pro") and CJK.search(s[:-3]):
        return s[:-3].strip(), "Pro"
    return s, None

def score_candidate(base, version, cand, rank):
    title = str(cand.get("trackName") or "")
    nb, nt = norm(base), norm(title)
    cb, ct = cj(base), cj(title)
    score = 0
    why = []

    if nb and nt and nb == nt:
        score = 310
        why.append("exact_normalized_title")
    if cb and ct and cb == ct:
        score = max(score, 300)
        why.append("exact_cjk_title")

    # Common App Store pattern: exact product name followed by a marketing slogan.
    if len(cb) >= 3 and ct.startswith(cb):
        score = max(score, 275)
        why.append("cjk_prefix_title")
    elif len(cb) >= 4 and cb in ct:
        score = max(score, 245)
        why.append("cjk_contains_title")

    # Mixed Latin+CJK brands such as B612咔叽.
    latin_tokens = "".join(re.findall(r"[A-Za-z0-9]+", base)).lower()
    if latin_tokens and latin_tokens in "".join(re.findall(r"[A-Za-z0-9]+", title)).lower():
        if cb and ct and (cb == ct or cb in ct):
            score = max(score, 285)
            why.append("mixed_brand_match")

    if str(version or "").strip() and str(cand.get("version") or "").strip() == str(version).strip():
        score += 35
        why.append("exact_version")

    # Search rank is only a tie-breaker, not proof.
    score += max(0, 8 - min(rank, 8))

    # Very short/generic Chinese names are ambiguous without exact normalized name or version.
    if len(cb) <= 2 and nb != nt and str(cand.get("version") or "").strip() != str(version or "").strip():
        score -= 80

    return score, why

def identify_one(item):
    base, version = item
    best = None
    best_score = -1
    best_why = []
    for rank, cand in enumerate(search_cn(base)):
        s, why = score_candidate(base, version, cand, rank)
        if s > best_score:
            best, best_score, best_why = cand, s, why
    threshold = 250 if len(cj(base)) <= 2 else 240
    if best and best_score >= threshold and best.get("trackId"):
        return {
            "base": base,
            "status": "identified",
            "trackId": int(best["trackId"]),
            "cnTrackName": best.get("trackName"),
            "cnVersion": best.get("version"),
            "developer": best.get("artistName") or best.get("sellerName"),
            "score": best_score,
            "reasons": best_why,
        }
    return {"base": base, "status": "unidentified", "score": max(best_score, 0)}

def main():
    current = json.loads(APPS_PATH.read_text(encoding="utf-8"))
    live = http_json(KUKA_URL, retries=4, timeout=30)
    if not isinstance(live, dict) or not isinstance(live.get("apps"), list):
        raise SystemExit("Kuka live source unavailable or malformed")

    live_apps = [a for a in live["apps"] if str(a.get("name") or "") != "‼️公告内容‼️"]
    apps = current.get("apps") or []
    if len(live_apps) != len(apps):
        raise SystemExit(f"Catalog count mismatch: live={len(live_apps)} current={len(apps)}")

    targets = []
    unique = {}
    for i, (src, dst) in enumerate(zip(live_apps, apps)):
        original = str(src.get("name") or "").strip()
        if not CJK.search(original):
            continue
        base, variant = split_variant(original)
        version = str(src.get("version") or dst.get("version") or "").strip()
        targets.append((i, original, base, variant, version))
        unique.setdefault(base, version)

    identified = {}
    items = list(unique.items())
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
        for r in ex.map(identify_one, items):
            identified[r["base"]] = r

    track_ids = sorted({r["trackId"] for r in identified.values() if r.get("trackId")})
    chunks = [track_ids[i:i+180] for i in range(0, len(track_ids), 180)]
    countries = ("vn", "us", "sg", "gb", "au")
    store = {c: {} for c in countries}

    jobs = [(c, ch) for c in countries for ch in chunks]
    def lookup_job(job):
        c, ch = job
        return c, batch_lookup(ch, c)

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        for c, result in ex.map(lookup_job, jobs):
            store[c].update(result)

    resolutions = {}
    for base, ident in identified.items():
        tid = ident.get("trackId")
        english = None
        storefront = None
        if tid:
            for c in countries:
                rr = store[c].get(tid)
                if not rr:
                    continue
                title = str(rr.get("trackName") or "").strip()
                if LATIN.search(title) and not CJK.search(title):
                    english = title
                    storefront = c
                    break
            if not english:
                cn_title = str(ident.get("cnTrackName") or "").strip()
                if LATIN.search(cn_title) and not CJK.search(cn_title):
                    english = cn_title
                    storefront = "cn"
        if english:
            resolutions[base] = {**ident, "status": "apple", "english": english, "storefront": storefront}
        elif base in CURATED:
            resolutions[base] = {**ident, "status": "curated", "english": CURATED[base], "storefront": None}
        else:
            resolutions[base] = {**ident, "status": "unresolved", "english": None, "storefront": None}

    # Curated fallbacks for bases Apple could not identify at all.
    for base in unique:
        if base not in resolutions:
            if base in CURATED:
                resolutions[base] = {"base": base, "status": "curated", "english": CURATED[base]}
            else:
                resolutions[base] = {"base": base, "status": "unresolved", "english": None}

    rows = []
    changed = 0
    counts = {"apple": 0, "curated": 0, "unresolved": 0}
    for i, original, base, variant, version in targets:
        r = resolutions[base]
        english = str(r.get("english") or "").strip()
        if english:
            final = f"{english} - {variant} ({original})" if variant else f"{english} ({original})"
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        else:
            final = original
            counts["unresolved"] += 1
        old = str(apps[i].get("name") or "")
        if old != final:
            apps[i]["name"] = final
            changed += 1
        rows.append({
            "index": i,
            "original": original,
            "old": old,
            "new": final,
            "base": base,
            "variant": variant,
            "status": r.get("status"),
            "trackId": r.get("trackId"),
            "cnTrackName": r.get("cnTrackName"),
            "storefront": r.get("storefront"),
            "score": r.get("score"),
            "reasons": r.get("reasons"),
            "developer": r.get("developer"),
        })

    # Strict QA: unresolved records must remain exactly the original Kuka name.
    bad = [x for x in rows if x["status"] == "unresolved" and x["new"] != x["original"]]
    if bad:
        raise SystemExit(f"QA failed: {len(bad)} unresolved names were modified")

    # Explicit regression checks for the cases that exposed the previous matcher weakness.
    wuta = [x for x in rows if x["original"] == "无他相机"]
    if wuta and not all(x["new"].startswith("Wuta Camera - Nice Shot Always (无他相机)") for x in wuta):
        raise SystemExit("QA failed: 无他相机 was not normalized to Wuta Camera")
    soul = [x for x in rows if x["original"] == "元气骑士"]
    if soul and not all(x["new"].startswith("Soul Knight (元气骑士)") for x in soul):
        raise SystemExit("QA failed: 元气骑士 was not normalized to Soul Knight")

    current["apps"] = apps
    APPS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "catalogApps": len(apps),
        "cjkTargets": len(targets),
        "uniqueBases": len(unique),
        "identifiedTrackIds": len(track_ids),
        "changed": changed,
        "appleResolved": counts.get("apple", 0),
        "curatedResolved": counts.get("curated", 0),
        "unresolvedKeptOriginal": counts.get("unresolved", 0),
        "rows": rows,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
