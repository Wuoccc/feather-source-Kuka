import json
p="apps.json"
m={
"112接线员":"112 Operator (112接线员)",
"777影视":"777 Movies (777影视)",
"777 影视":"777 Movies (777 影视)",
"30天内练出六块腹肌":"Six Pack in 30 Days - 6 Pack (30天内练出六块腹肌)",
"168轻断食":"Intermittent Fasting Tracker (168轻断食)",
"8毫米相机":"8mm Vintage Camera (8毫米相机)",
"2024人体解剖学图谱":"Human Anatomy Atlas 2024 (2024人体解剖学图谱)",
"2023人体解剖学图谱":"Human Anatomy Atlas 2024 (2023人体解剖学图谱)",
"360行车记录仪":"360 Dash Cam (360行车记录仪)",
"555电影":"555 Movies (555电影)"
}
with open(p,"r",encoding="utf-8") as f:d=json.load(f)
changed=0
for a in d.get("apps",[]):
    n=a.get("name")
    if n in m:
        a["name"]=m[n]
        changed+=1
with open(p,"w",encoding="utf-8") as f:
    json.dump(d,f,ensure_ascii=False,indent=2)
    f.write("\n")
print("changed",changed)
