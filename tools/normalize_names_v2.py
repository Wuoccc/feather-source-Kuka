import concurrent.futures
import difflib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

APPS_PATH = Path("apps.json")
REPORT_PATH = Path(".name-normalization-v2-report.json")
KUKA_URL = "https://app.ioskuka.com/appstore"
UA = "Mozilla/5.0 (Kuka Feather Name Normalizer/2.0)"

CJK = re.compile(r"[\u3400-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")

# Mod/variant suffixes are not App Store product names. Resolve the base app,
# then append a neutral English variant label while retaining the full Kuka
# original name in parentheses.
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

# High-confidence established international names. These are only fallbacks
# when Apple resolution cannot produce a Latin storefront title.
CURATED = {
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

def http_json(url, retries=4, timeout=25):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e
            time.sleep(0.5 * (i + 1))
    return None

def normalize_text(s):
    s = str(s or "").lower()
    s = re.sub(r"[\s\-—–_:：·•・,，.。!！?？'’\"“”()（）\[\]【】/+]+", "", s)
    return s

def cjk_only(s):
    return "".join(CJK.findall(str(s or "")))

def split_variant(name):
    s = str(name or "").strip()
    for zh, en in VARIANTS:
        if s.endswith(zh) and len(s) > len(zh):
            return s[:-len(zh)].strip(" -—–_:："), en
    if s.lower().endswith("pro") and CJK.search(s[:-3]):
        return s[:-3].strip(), "Pro"
    return s, None

def apple_search(term, country="cn", limit=50):
    qs = urllib.parse.urlencode({
        "term": term,
        "country": country,
        "entity": "software",
        "limit": limit,
    })
    data = http_json("https://itunes.apple.com/search?" + qs)
    if isinstance(data, dict):
        return data.get("results") or []
    return []

def apple_lookup(track_id, country):
    qs = urllib.parse.urlencode({"id": str(track_id), "country": country, "entity": "software"})
    data = http_json("https://itunes.apple.com/lookup?" + qs)
    if isinstance(data, dict) and data.get("resultCount"):
        rs = data.get("results") or []
        return rs[0] if rs else None
    return None

def candidate_score(base, app_version, cand):
    title = str(cand.get("trackName") or "")
    nb = normalize_text(base)
    nt = normalize_text(title)
    if not nb or not nt:
        return 0
    cb = cjk_only(base)
    ct = cjk_only(title)
    score = 0
    if nt == nb:
        score = 260
    elif nb in nt or nt in nb:
        ratio = min(len(nb), len(nt)) / max(len(nb), len(nt))
        if ratio >= 0.62:
            score = 225
    if cb and ct:
        if cb == ct:
            score = max(score, 250)
        elif cb in ct or ct in cb:
            ratio = min(len(cb), len(ct)) / max(len(cb), len(ct))
            if ratio >= 0.60:
                score = max(score, 220)
        else:
            ratio = difflib.SequenceMatcher(None, cb, ct).ratio()
            if ratio >= 0.90:
                score = max(score, 210)
            elif ratio >= 0.82:
                score = max(score, 185)
    ratio_all = difflib.SequenceMatcher(None, nb, nt).ratio()
    if ratio_all >= 0.92:
        score = max(score, 220)
    elif ratio_all >= 0.84:
        score = max(score, 190)
    cv = str(cand.get("version") or "").strip()
    av = str(app_version or "").strip()
    if av and cv and av == cv:
        score += 25
    # Generic very-short names are ambiguous unless version also matches.
    if len(cb) <= 2 and str(cand.get("version") or "").strip() != str(app_version or "").strip():
        score -= 45
    return score

def find_cn_candidate(base, version):
    terms = [base]
    compact = re.sub(r"\s+", " ", base).strip()
    if compact != base:
        terms.append(compact)
    best = None
    best_score = 0
    seen = set()
    for term in terms:
        for cand in apple_search(term, "cn", 50):
            tid = cand.get("trackId")
            if not tid or tid in seen:
                continue
            seen.add(tid)
            s = candidate_score(base, version, cand)
            if s > best_score:
                best_score, best = s, cand
        if best_score >= 245:
            break
    # Distinctive names can resolve without exact version. Generic names need more.
    min_score = 205 if len(cjk_only(base)) >= 3 else 225
    if best is not None and best_score >= min_score:
        return best, best_score
    return None, best_score

def latin_title_from_track(track_id, cn_cand):
    # Prefer VN, then English-heavy storefronts.
    for country in ("vn", "us", "sg", "gb", "au"):
        r = apple_lookup(track_id, country)
        if not r:
            continue
        title = str(r.get("trackName") or "").strip()
        if LATIN.search(title) and not CJK.search(title):
            return title, country, r
    title = str((cn_cand or {}).get("trackName") or "").strip()
    if LATIN.search(title) and not CJK.search(title):
        return title, "cn", cn_cand
    return None, None, None

def resolve_one(args):
    base, version = args
    cand, score = find_cn_candidate(base, version)
    if cand:
        title, country, rr = latin_title_from_track(cand.get("trackId"), cand)
        if title:
            return {
                "base": base,
                "status": "apple",
                "english": title,
                "trackId": cand.get("trackId"),
                "cnTrackName": cand.get("trackName"),
                "storefront": country,
                "score": score,
                "developer": cand.get("artistName"),
            }
    # If China search did not resolve, try direct VN/US searches for mixed names.
    best = None
    best_score = 0
    best_country = None
    for country in ("vn", "us"):
        for cand2 in apple_search(base, country, 50):
            s = candidate_score(base, version, cand2)
            title = str(cand2.get("trackName") or "").strip()
            if s > best_score and LATIN.search(title) and not CJK.search(title):
                best, best_score, best_country = cand2, s, country
    if best is not None and best_score >= 225:
        return {
            "base": base,
            "status": "apple",
            "english": str(best.get("trackName") or "").strip(),
            "trackId": best.get("trackId"),
            "cnTrackName": None,
            "storefront": best_country,
            "score": best_score,
            "developer": best.get("artistName"),
        }
    if base in CURATED:
        return {"base": base, "status": "curated", "english": CURATED[base]}
    return {"base": base, "status": "unresolved", "english": None}

def main():
    current = json.loads(APPS_PATH.read_text(encoding="utf-8"))
    live = http_json(KUKA_URL, retries=5, timeout=60)
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

    resolutions = {}
    items = list(unique.items())
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(resolve_one, item): item[0] for item in items}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            base = futs[fut]
            try:
                resolutions[base] = fut.result()
            except Exception as e:
                resolutions[base] = {"base": base, "status": "error", "english": None, "error": str(e)}
            done += 1
            if done % 100 == 0:
                print(f"resolved {done}/{len(items)}")

    changed = 0
    apple_count = 0
    curated_count = 0
    unresolved_count = 0
    rows = []

    for i, original, base, variant, version in targets:
        r = resolutions.get(base) or {"status": "unresolved", "english": None}
        english = str(r.get("english") or "").strip()
        status = r.get("status") or "unresolved"
        if english:
            if variant:
                final_name = f"{english} - {variant} ({original})"
            else:
                final_name = f"{english} ({original})"
            if status == "apple":
                apple_count += 1
            else:
                curated_count += 1
        else:
            final_name = original
            unresolved_count += 1

        old_name = str(apps[i].get("name") or "")
        if old_name != final_name:
            apps[i]["name"] = final_name
            changed += 1

        rows.append({
            "index": i,
            "original": original,
            "old": old_name,
            "new": final_name,
            "base": base,
            "variant": variant,
            "status": status,
            "trackId": r.get("trackId"),
            "storefront": r.get("storefront"),
            "score": r.get("score"),
            "developer": r.get("developer"),
            "cnTrackName": r.get("cnTrackName"),
        })

    # QA: never accept a translated/invented English name. Every Latinized result
    # must be Apple-resolved or curated; unresolved names stay byte-for-byte Kuka.
    invalid = []
    for row in rows:
        if row["status"] in ("unresolved", "error"):
            if row["new"] != row["original"]:
                invalid.append(row)
        else:
            if row["original"] not in row["new"]:
                invalid.append(row)
    if invalid:
        raise SystemExit(f"QA failed: {len(invalid)} invalid name rows")

    current["apps"] = apps
    APPS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "catalogApps": len(apps),
        "cjkTargets": len(targets),
        "uniqueBases": len(unique),
        "changed": changed,
        "appleResolved": apple_count,
        "curatedResolved": curated_count,
        "unresolvedKeptOriginal": unresolved_count,
        "rows": rows,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "rows"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
