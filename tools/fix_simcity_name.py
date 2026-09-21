import json
p="apps.json"
with open(p,"r",encoding="utf-8") as f:
    d=json.load(f)
n=0
for a in d.get("apps",[]):
    if a.get("name")=="模拟城市":
        a["name"]="SimCity BuildIt (模拟城市)"
        n+=1
with open(p,"w",encoding="utf-8") as f:
    json.dump(d,f,ensure_ascii=False,indent=2)
    f.write("\n")
print("renamed",n)
