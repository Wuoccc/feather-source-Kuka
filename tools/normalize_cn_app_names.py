import json

PATH = "apps.json"

# Only high-confidence, manually verified / well-established official international names.
# Exact-match mapping only: no fuzzy rename, no automatic translation.
NAME_MAP = {
    "元气骑士": "Soul Knight (元气骑士)",
    "WeChat": "WeChat (微信)",
    "微信": "WeChat (微信)",
    "rednote": "rednote (小红书)",
    "小红书": "rednote (小红书)",
    "Alipay - Simplify Your Life": "Alipay (支付宝)",
    "支付宝": "Alipay (支付宝)",
    "WeCom": "WeCom (企业微信)",
    "企业微信": "WeCom (企业微信)",
    "Duolingo: Language & Chess": "Duolingo (多邻国)",
    "多邻国": "Duolingo (多邻国)",
    "网易云音乐": "NetEase Cloud Music (网易云音乐)",
    "酷狗音乐": "KuGou Music (酷狗音乐)",
    "酷我音乐": "Kuwo Music (酷我音乐)",
    "百度网盘": "Baidu Netdisk (百度网盘)",
    "哔哩哔哩": "bilibili (哔哩哔哩)",
    "QQ音乐": "QQ Music (QQ音乐)",
    "微博": "Weibo (微博)",
    "知乎": "Zhihu (知乎)",
    "淘宝": "Taobao (淘宝)",
    "京东": "JD.com (京东)",
    "拼多多": "Pinduoduo (拼多多)",
    "美团": "Meituan (美团)",
    "饿了么": "Ele.me (饿了么)",
    "高德地图": "Amap (高德地图)",
    "百度地图": "Baidu Maps (百度地图)",
    "百度贴吧": "Baidu Tieba (百度贴吧)",
    "钉钉": "DingTalk (钉钉)",
    "飞书": "Feishu (飞书)",
    "今日头条": "Toutiao (今日头条)",
    "快手": "Kuaishou (快手)",
    "优酷": "YOUKU (优酷)",
    "爱奇艺": "iQIYI (爱奇艺)",
    "喜马拉雅": "Ximalaya (喜马拉雅)",
    "豆瓣": "Douban (豆瓣)",
    "百度": "Baidu (百度)",
    "UC浏览器": "UC Browser (UC浏览器)",
    "夸克浏览器": "Quark Browser (夸克浏览器)",
    "夸克": "Quark (夸克)",
    "王者荣耀": "Honor of Kings (王者荣耀)",
    "原神": "Genshin Impact (原神)",
    "崩坏：星穹铁道": "Honkai: Star Rail (崩坏：星穹铁道)",
    "崩坏:星穹铁道": "Honkai: Star Rail (崩坏:星穹铁道)",
    "崩坏3": "Honkai Impact 3rd (崩坏3)",
    "明日方舟": "Arknights (明日方舟)",
    "第五人格": "Identity V (第五人格)",
    "蛋仔派对": "Eggy Party (蛋仔派对)",
    "鸣潮": "Wuthering Waves (鸣潮)",
    "绝区零": "Zenless Zone Zero (绝区零)",
    "恋与深空": "Love and Deepspace (恋与深空)",
    "光·遇": "Sky: Children of the Light (光·遇)",
    "光遇": "Sky: Children of the Light (光遇)"
}

with open(PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

apps = data.get("apps")
if not isinstance(apps, list) or not apps:
    raise SystemExit("apps is missing or empty")

changed = []
for app in apps:
    if not isinstance(app, dict):
        continue
    old = app.get("name")
    if old in NAME_MAP and NAME_MAP[old] != old:
        new = NAME_MAP[old]
        app["name"] = new
        changed.append((old, new))

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"Renamed {len(changed)} app entries")
for old, new in changed[:100]:
    print(f"{old} -> {new}")
