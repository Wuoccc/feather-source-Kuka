import concurrent.futures
import json
import re
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import normalize_names_v4 as v4

REPORT_PATH = Path(".name-normalization-v5-report.json")

# Additional names verified against Apple/global App Store naming.
CURATED = dict(v4.CURATED)
CURATED.update({
    "星露谷物语": "Stardew Valley",
    "星露谷物语+": "Stardew Valley+",
    "部落冲突": "Clash of Clans",
    "皇室战争": "Clash Royale",
    "地铁跑酷": "Subway Surfers",
    "植物大战僵尸2": "Plants vs. Zombies™ 2",
    "死亡细胞": "Dead Cells",
})

# Treat trailing 国际 as a variant only when there is a non-empty Chinese base.
VARIANTS = list(v4.VARIANTS)
VARIANTS.insert(4, ("国际", "International"))

_rate_lock = threading.Lock()
_next_request = 0.0

def rate_wait():
    global _next_request
    with _rate_lock:
        now = time.monotonic()
        if now < _next_request:
            time.sleep(_next_request - now)
        _next_request = time.monotonic() + 0.50

def http_json(url, retries=3, timeout=12):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": v4.UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            time.sleep(0.8 * (attempt + 1))
    return {}

def search_cn(term):
    rate_wait()
    q = urllib.parse.urlencode({"term": term, "country": "cn", "entity": "software", "limit": 15})
    d = http_json("https://itunes.apple.com/search?" + q)
    return d.get("results", []) if isinstance(d, dict) else []

def strict_score(base, version, cand, rank):
    title = str(cand.get("trackName") or "").strip()
    nb, nt = v4.norm(base), v4.norm(title)
    cb, ct = v4.cj(base), v4.cj(title)
    same_ver = bool(version and str(cand.get("version") or "").strip() == version)
    score = 0
    reasons = []

    # Strong identity evidence only.
    if nb and nt and nb == nt:
        score = 400
        reasons.append("exact_normalized_title")
    if cb and ct and cb == ct:
        score = max(score, 390)
        reasons.append("exact_cjk_title")

    # Marketing-slogan title is accepted only with exact Kuka/App Store version.
    if same_ver and len(cb) >= 3 and (ct.startswith(cb) or cb in ct):
        score = max(score, 360)
        reasons.append("version_plus_cjk_title")

    if same_ver:
        score += 40
        reasons.append("exact_version")
    score += max(0, 5 - min(rank, 5))
    return score, reasons

def extract_cn_official_latin(title, base):
    # Only extract an explicit Latin alias that Apple itself shows in parentheses,
    # e.g. 部落冲突（Clash of Clans）.
    s = str(title or "").strip()
    cb = v4.cj(base)
    ct = v4.cj(s)
    if not cb or cb != ct:
        return None
    for m in re.finditer(r"[（(]([^()（）]+)[）)]", s):
        part = m.group(1).strip()
        if v4.LATIN.search(part) and not v4.CJK.search(part) and len(part) >= 4:
            # Reject acronym-only aliases such as CR.
            letters = re.sub(r"[^A-Za-z]", "", part)
            if len(letters) >= 4:
                return part
    return None

def identify_one(item):
    base, version = item
    best = None
    best_score = -1
    best_reasons = []
    for rank, cand in enumerate(search_cn(base)):
        score, reasons = strict_score(base, version, cand, rank)
        if score > best_score:
            best, best_score, best_reasons = cand, score, reasons
    if best and best_score >= 390 and best.get("trackId"):
        return {
            "base": base,
            "status": "identified",
            "trackId": int(best["trackId"]),
            "cnTrackName": best.get("trackName"),
            "cnVersion": best.get("version"),
            "developer": best.get("artistName") or best.get("sellerName"),
            "score": best_score,
            "reasons": best_reasons,
            "cnLatinAlias": extract_cn_official_latin(best.get("trackName"), base),
        }
    return {"base": base, "status": "unidentified", "score": max(best_score, 0)}

def split_variant(name):
    s = str(name or "").strip()
    for zh, en in VARIANTS:
        if s.endswith(zh) and len(s) > len(zh):
            return s[:-len(zh)].strip(" -—–_:："), en
    if s.lower().endswith("pro") and v4.CJK.search(s[:-3]):
        return s[:-3].strip(), "Pro"
    return s, None

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

def main():
    current = json.loads(v4.APPS_PATH.read_text(encoding="utf-8"))
    apps = current.get("apps") or []
    live = v4.http_json(v4.KUKA_URL, retries=4, timeout=30)
    if not isinstance(live, dict) or not isinstance(live.get("apps"), list):
        raise SystemExit("Kuka live source unavailable or malformed")
    live_apps = [a for a in live["apps"] if str(a.get("name") or "") != "‼️公告内容‼️"]
    if len(live_apps) != len(apps):
        raise SystemExit(f"Catalog count mismatch live={len(live_apps)} current={len(apps)}")

    hints = v4.build_hints(apps)
    mapping, map_meta = v4.map_live_to_current(live_apps, apps, hints)

    targets = []
    unique = {}
    for live_i, src in enumerate(live_apps):
        original = str(src.get("name") or "").strip()
        if not v4.CJK.search(original):
            continue
        cur_i = mapping[live_i]
        base, variant = split_variant(original)
        version = str(src.get("version") or apps[cur_i].get("version") or "").strip()
        targets.append((live_i, cur_i, original, base, variant, version))
        unique.setdefault(base, version)

    # Curated bases do not need Apple search again.
    search_items = [(b, ver) for b, ver in unique.items() if b not in CURATED]
    identified = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(identify_one, search_items):
            identified[r["base"]] = r

    track_ids = sorted({r["trackId"] for r in identified.values() if r.get("trackId")})
    chunks = [track_ids[i:i+180] for i in range(0, len(track_ids), 180)]
    countries = ("vn", "us", "sg", "gb", "au")
    store = {c: {} for c in countries}
    jobs = [(c, ch) for c in countries for ch in chunks]

    def lookup_job(job):
        c, ch = job
        return c, batch_lookup(ch, c)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for c, result in ex.map(lookup_job, jobs):
            store[c].update(result)

    resolutions = {}
    for base in unique:
        if base in CURATED:
            resolutions[base] = {"base": base, "status": "curated", "english": CURATED[base]}
            continue
        ident = identified.get(base) or {"base": base, "status": "unidentified"}
        tid = ident.get("trackId")
        english = None
        storefront = None
        if tid:
            for c in countries:
                rr = store[c].get(tid)
                if not rr:
                    continue
                title = str(rr.get("trackName") or "").strip()
                if v4.LATIN.search(title) and not v4.CJK.search(title):
                    english = title
                    storefront = c
                    break
            if not english and ident.get("cnLatinAlias"):
                english = ident["cnLatinAlias"]
                storefront = "cn-title-alias"
        if english:
            resolutions[base] = {**ident, "status": "apple", "english": english, "storefront": storefront}
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

    if len(mapping) != len(apps):
        raise SystemExit("Catalog identity mapping incomplete")
    if any(x["mapping"]["score"] < 200 for x in rows):
        raise SystemExit("Weak record identity mapping")
    if any(x["status"] == "unresolved" and x["new"] != x["original"] for x in rows):
        raise SystemExit("Unresolved name was modified")

    checks = {
        "无他相机": "Wuta Camera - Nice Shot Always (无他相机)",
        "元气骑士": "Soul Knight (元气骑士)",
        "星露谷物语": "Stardew Valley (星露谷物语)",
        "死亡细胞": "Dead Cells (死亡细胞)",
        "部落冲突": "Clash of Clans (部落冲突)",
        "皇室战争": "Clash Royale (皇室战争)",
        "地铁跑酷": "Subway Surfers (地铁跑酷)",
        "植物大战僵尸2": "Plants vs. Zombies™ 2 (植物大战僵尸2)",
    }
    for original, expected in checks.items():
        rr = [x for x in rows if x["original"] == original]
        if rr and not all(x["new"] == expected for x in rr):
            raise SystemExit(f"Regression check failed for {original}: {[x['new'] for x in rr]}")

    current["apps"] = apps
    v4.APPS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "catalogApps": len(apps),
        "mappedCatalogApps": len(mapping),
        "cjkTargets": len(rows),
        "uniqueBases": len(unique),
        "searchedBases": len(search_items),
        "identifiedTrackIds": len(track_ids),
        "changed": changed,
        "appleResolved": counts.get("apple", 0),
        "curatedResolved": counts.get("curated", 0),
        "unresolvedKeptOriginal": counts.get("unresolved", 0),
        "rows": rows,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "rows"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
