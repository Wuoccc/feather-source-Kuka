import json
from datetime import datetime, timezone

PATH = "apps.json"

def parse_date(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    candidates = [s]
    if s.endswith("Z"):
        candidates.append(s[:-1] + "+00:00")
    for x in candidates:
        try:
            dt = datetime.fromisoformat(x)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None

def app_date(app):
    dt = parse_date(app.get("versionDate"))
    if dt is not None:
        return dt
    versions = app.get("versions")
    if isinstance(versions, list):
        dates = []
        for v in versions:
            if isinstance(v, dict):
                d = parse_date(v.get("date"))
                if d is not None:
                    dates.append(d)
        if dates:
            return max(dates)
    return None

with open(PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

apps = data.get("apps")
if not isinstance(apps, list) or not apps:
    raise SystemExit("apps is missing or empty")

decorated = []
for idx, app in enumerate(apps):
    dt = app_date(app) if isinstance(app, dict) else None
    decorated.append((dt, idx, app))

# Valid dates first, newest to oldest. Preserve original order for ties/no-date records.
decorated.sort(
    key=lambda item: (
        item[0] is not None,
        item[0].timestamp() if item[0] is not None else 0,
        -item[1],
    ),
    reverse=True,
)

data["apps"] = [item[2] for item in decorated]

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

valid = sum(1 for dt, _, _ in decorated if dt is not None)
print(f"Sorted {len(apps)} apps; dated={valid}; undated={len(apps)-valid}")
