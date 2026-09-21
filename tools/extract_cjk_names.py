import json,re
p="apps.json"
out="cjk_names.json"
rx=re.compile(r"[\u3400-\u9fff]")
with open(p,"r",encoding="utf-8") as f:
    d=json.load(f)
rows=[]
for i,a in enumerate(d.get("apps",[])):
    name=str(a.get("name",""))
    if rx.search(name):
        rows.append({
            "index":i,
            "name":name,
            "version":a.get("version"),
            "developerName":a.get("developerName"),
            "bundleIdentifier":a.get("bundleIdentifier"),
            "iconURL":a.get("iconURL"),
            "subtitle":a.get("subtitle"),
            "localizedDescription":a.get("localizedDescription")
        })
with open(out,"w",encoding="utf-8") as f:
    json.dump(rows,f,ensure_ascii=False,indent=2)
    f.write("\n")
print(len(rows))
