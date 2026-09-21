import concurrent.futures
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

APPS_PATH = Path("apps.json")
REPORT_PATH = Path(".name-normalization-v4-report.json")
KUKA_URL = "https://app.ioskuka.com/appstore"
UA = "Mozilla/5.0 (Kuka Feather Name Normalizer/4.0)"

CJK = re.compile(r"[\u3400-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")

HIST_CJK_COMMIT = "a353f85b6654295f0e3a126c28bd164cfab6d09a"
HIST_REPORT_COMMIT = "4a9a6af7436d432f2cc67d6a899f763d4879a321"

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

def http_json(url, retries=3, timeout=10):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            time.sleep(0.45 * (i + 1))
    return {}

def git_json(commit, path):
    raw = subprocess.check_output(["git", "show", f"{commit}:{path}"])
    return json.loads(raw.decode("utf-8"))

def basename_url(u):
    s = str(u or "").strip()
    if not s:
        return ""
    try:
        p = urllib.parse.urlparse(s)
        return os.path.basename(p.path).lower()
    except Exception:
        return s.rsplit("/", 1)[-1].lower()

def size_int(v):
    try:
        x = int(float(v))
        return x if x >= 0 else None
    except Exception:
        return None

def norm_url(u):
    s = str(u or "").strip()
    if not s:
        return ""
    s = re.sub(r"^http://", "https://", s, flags=re.I)
    return s

def feature(a):
    return {
        "name": str(a.get("name") or "").strip(),
        "icon": basename_url(a.get("iconURL")),
        "version": str(a.get("version") or "").strip(),
        "size": size_int(a.get("size")),
        "date": str(a.get("versionDate") or a.get("date") or "").strip(),
        "download": norm_url(a.get("downloadURL")),
    }

def extract_original_from_old_name(name):
    s = str(name or "").strip()
    pos = s.find(" (")
    if pos >= 0 and s.endswith(")"):
        inner = s[pos + 2:-1]
        if CJK.search(inner):
            return inner
    return s

def build_hints(current_apps):
    report = git_json(HIST_REPORT_COMMIT, "name_normalization_report.json")
    old_cjk = git_json(HIST_CJK_COMMIT, "cjk_names.json")
    hints = {}
    for r in report:
        if isinstance(r.get("index"), int) and r.get("original"):
            hints[r["index"]] = str(r["original"])
    for r in old_cjk:
        i = r.get("index")
        if not isinstance(i, int) or i in hints:
            continue
        n = str(r.get("name") or "")
        hints[i] = extract_original_from_old_name(n)
    for i, a in enumerate(current_apps):
        if i not in hints:
            hints[i] = extract_original_from_old_name(str(a.get("name") or ""))
    return hints

def map_live_to_current(live_apps, current_apps, hints):
    cf = [feature(a) for a in current_apps]
    by_name, by_icon, by_vsd, by_dl = {}, {}, {}, {}
    for i, f in enumerate(cf):
        for nm in {f["name"], hints.get(i, "")}:
            if nm:
                by_name.setdefault(nm, set()).add(i)
        if f["icon"]:
            by_icon.setdefault(f["icon"], set()).add(i)
        if f["version"] and f["size"] is not None and f["date"]:
            by_vsd.setdefault((f["version"], f["size"], f["date"]), set()).add(i)
        if f["download"]:
            by_dl.setdefault(f["download"], set()).add(i)

    all_options = []
    for j, a in enumerate(live_apps):
        lf = feature(a)
        cand = set()
        cand |= by_name.get(lf["name"], set())
        if lf["icon"]:
            cand |= by_icon.get(lf["icon"], set())
        if lf["version"] and lf["size"] is not None and lf["date"]:
            cand |= by_vsd.get((lf["version"], lf["size"], lf["date"]), set())
        if lf["download"]:
            cand |= by_dl.get(lf["download"], set())
        scored = []
        for i in cand:
            f = cf[i]
            score = 0
            reasons = []
            if hints.get(i) == lf["name"]:
                score += 520; reasons.append("original_name")
            elif f["name"] == lf["name"]:
                score += 500; reasons.append("display_name")
            if lf["download"] and f["download"] == lf["download"]:
                score += 260; reasons.append("download")
            if lf["icon"] and f["icon"] == lf["icon"]:
                score += 190; reasons.append("icon")
            if lf["version"] and f["version"] == lf["version"]:
                score += 70; reasons.append("version")
            if lf["size"] is not None and f["size"] == lf["size"]:
                score += 70; reasons.append("size")
            if lf["date"] and f["date"] == lf["date"]:
                score += 70; reasons.append("date")
            if score:
                scored.append((score, i, reasons))
        scored.sort(reverse=True, key=lambda x: x[0])
        all_options.append((j, lf, scored))

    order = []
    for j, lf, opts in all_options:
        best = opts[0][0] if opts else -1
        second = opts[1][0] if len(opts) > 1 else -1
        order.append((best - second, best, j, lf, opts))
    order.sort(reverse=True)

    used = set()
    mapping = {}
    map_meta = {}
    for margin, best, j, lf, opts in order:
        picked = None
        for score, i, reasons in opts:
            if i not in used:
                picked = (score, i, reasons)
                break
        if picked:
            score, i, reasons = picked
            mapping[j] = i
            used.add(i)
            map_meta[j] = {"currentIndex": i, "score": score, "reasons": reasons}

    # Only accept complete one-to-one mapping. The catalog counts are equal, so
    # missing mappings indicate unsafe alignment and must block writes.
    if len(mapping) != len(live_apps):
        missing = [j for j in range(len(live_apps)) if j not in mapping][:30]
        raise SystemExit(f"Mapping incomplete: {len(mapping)}/{len(live_apps)}; missing={missing}")

    weak = [(j, map_meta[j]) for j in mapping if map_meta[j]["score"] < 200]
    if weak:
        raise SystemExit(f"Mapping has {len(weak)} weak matches under score 200; sample={weak[:10]}")

    return mapping, map_meta

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

def apple_search_cn(term):
    q = urllib.parse.urlencode({"term": term, "country": "cn", "entity": "software", "limit": 30})
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
            if r.get("trackId") is not None:
                out[int(r["trackId"])] = r
    return out

def score_apple(base, version, cand, rank):
    title = str(cand.get("trackName") or "")
    nb, nt = norm(base), norm(title)
    cb, ct = cj(base), cj(title)
    score = 0
    why = []
    if nb and nb == nt:
        score = 320; why.append("exact_normalized_title")
    if cb and cb == ct:
        score = max(score, 310); why.append("exact_cjk_title")
    if len(cb) >= 3 and ct.startswith(cb):
        score = max(score, 285); why.append("cjk_prefix_title")
    elif len(cb) >= 4 and cb in ct:
        score = max(score, 255); why.append("cjk_contains_title")
    latin_base = "".join(re.findall(r"[A-Za-z0-9]+", base)).lower()
    latin_title = "".join(re.findall(r"[A-Za-z0-9]+", title)).lower()
    if latin_base and latin_base in latin_title and cb and ct and (cb == ct or cb in ct):
        score = max(score, 295); why.append("mixed_brand")
    if version and str(cand.get("version") or "").strip() == version:
        score += 35; why.append("exact_version")
    score += max(0, 6 - min(rank, 6))
    if len(cb) <= 2 and nb != nt and str(cand.get("version") or "").strip() != version:
        score -= 90
    return score, why

def identify_one(item):
    base, version = item
    best = None; best_score = -1; best_why = []
    for rank, cand in enumerate(apple_search_cn(base)):
        s, why = score_apple(base, version, cand, rank)
        if s > best_score:
            best, best_score, best_why = cand, s, why
    threshold = 260 if len(cj(base)) <= 2 else 245
    if best and best_score >= threshold and best.get("trackId"):
        return {
            "base": base, "status": "identified", "trackId": int(best["trackId"]),
            "cnTrackName": best.get("trackName"), "cnVersion": best.get("version"),
            "developer": best.get("artistName") or best.get("sellerName"),
            "score": best_score, "reasons": best_why,
        }
    return {"base": base, "status": "unidentified", "score": max(best_score, 0)}

def main():
    current = json.loads(APPS_PATH.read_text(encoding="utf-8"))
    apps = current.get("apps") or []
    live = http_json(KUKA_URL, retries=4, timeout=30)
    if not isinstance(live, dict) or not isinstance(live.get("apps"), list):
        raise SystemExit("Kuka live source unavailable or malformed")
    live_apps = [a for a in live["apps"] if str(a.get("name") or "") != "‼️公告内容‼️"]
    if len(live_apps) != len(apps):
        raise SystemExit(f"Catalog count mismatch live={len(live_apps)} current={len(apps)}")

    hints = build_hints(apps)
    mapping, map_meta = map_live_to_current(live_apps, apps, hints)

    targets = []
    unique = {}
    for live_i, src in enumerate(live_apps):
        original = str(src.get("name") or "").strip()
        if not CJK.search(original):
            continue
        cur_i = mapping[live_i]
        base, variant = split_variant(original)
        version = str(src.get("version") or apps[cur_i].get("version") or "").strip()
        targets.append((live_i, cur_i, original, base, variant, version))
        unique.setdefault(base, version)

    identified = {}
    items = list(unique.items())
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(identify_one, items):
            identified[r["base"]] = r

    track_ids = sorted({r["trackId"] for r in identified.values() if r.get("trackId")})
    chunks = [track_ids[i:i+180] for i in range(0, len(track_ids), 180)]
    countries = ("vn", "us", "sg", "gb", "au")
    store = {c: {} for c in countries}
    jobs = [(c, ch) for c in countries for ch in chunks]
    def lj(job):
        c, ch = job
        return c, batch_lookup(ch, c)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for c, result in ex.map(lj, jobs):
            store[c].update(result)

    resolutions = {}
    for base in unique:
        ident = identified.get(base) or {"base": base, "status": "unidentified"}
        tid = ident.get("trackId")
        english = None; storefront = None
        if tid:
            for c in countries:
                rr = store[c].get(tid)
                if not rr:
                    continue
                title = str(rr.get("trackName") or "").strip()
                if LATIN.search(title) and not CJK.search(title):
                    english = title; storefront = c; break
            if not english:
                cn_title = str(ident.get("cnTrackName") or "").strip()
                if LATIN.search(cn_title) and not CJK.search(cn_title):
                    english = cn_title; storefront = "cn"
        if english:
            resolutions[base] = {**ident, "status": "apple", "english": english, "storefront": storefront}
        elif base in CURATED:
            resolutions[base] = {**ident, "status": "curated", "english": CURATED[base], "storefront": None}
        else:
            resolutions[base] = {**ident, "status": "unresolved", "english": None, "storefront": None}

    rows = []
    changed = 0
    counts = {"apple": 0, "curated": 0, "unresolved": 0}
    touched = set()
    for live_i, cur_i, original, base, variant, version in targets:
        if cur_i in touched:
            raise SystemExit(f"Duplicate current target index {cur_i}")
        touched.add(cur_i)
        r = resolutions[base]
        english = str(r.get("english") or "").strip()
        if english:
            final = f"{english} - {variant} ({original})" if variant else f"{english} ({original})"
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        else:
            final = original
            counts["unresolved"] += 1
        old = str(apps[cur_i].get("name") or "")
        if old != final:
            apps[cur_i]["name"] = final
            changed += 1
        rows.append({
            "liveIndex": live_i, "currentIndex": cur_i, "original": original,
            "old": old, "new": final, "base": base, "variant": variant,
            "status": r.get("status"), "trackId": r.get("trackId"),
            "cnTrackName": r.get("cnTrackName"), "storefront": r.get("storefront"),
            "score": r.get("score"), "reasons": r.get("reasons"),
            "developer": r.get("developer"), "mapping": map_meta[live_i],
        })

    if len(rows) != sum(1 for a in live_apps if CJK.search(str(a.get("name") or ""))):
        raise SystemExit("CJK target count mismatch after mapping")
    if any(x["status"] == "unresolved" and x["new"] != x["original"] for x in rows):
        raise SystemExit("Unresolved name modified")
    if any(x["original"] not in x["new"] for x in rows if x["status"] != "unresolved"):
        raise SystemExit("Resolved name lost Kuka original")

    wuta = [x for x in rows if x["original"] == "无他相机"]
    if wuta and not all(x["new"] == "Wuta Camera - Nice Shot Always (无他相机)" for x in wuta):
        raise SystemExit("Wuta regression check failed")
    soul = [x for x in rows if x["original"] == "元气骑士"]
    if soul and not all(x["new"] == "Soul Knight (元气骑士)" for x in soul):
        raise SystemExit("Soul Knight regression check failed")

    current["apps"] = apps
    APPS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "catalogApps": len(apps), "mappedCatalogApps": len(mapping),
        "cjkTargets": len(rows), "uniqueBases": len(unique),
        "identifiedTrackIds": len(track_ids), "changed": changed,
        "appleResolved": counts.get("apple", 0),
        "curatedResolved": counts.get("curated", 0),
        "unresolvedKeptOriginal": counts.get("unresolved", 0),
        "rows": rows,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "rows"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
