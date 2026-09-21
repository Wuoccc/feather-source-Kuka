import json,re
p="apps.json"; out="name_qa.json"
cjk=re.compile(r"[\u3400-\u9fff]"); latin=re.compile(r"[A-Za-z]")
with open(p,"r",encoding="utf-8") as f:d=json.load(f)
apps=d.get("apps",[])
bad=[]; total_cjk=0; starts_cjk=0; no_latin_before=0
for i,a in enumerate(apps):
    n=str(a.get("name",""))
    m=cjk.search(n)
    if not m: continue
    total_cjk+=1
    if cjk.search(n.lstrip()[:1] or ""): starts_cjk+=1
    if not latin.search(n[:m.start()]):
        no_latin_before+=1
        if len(bad)<50: bad.append({"index":i,"name":n})
q={"apps":len(apps),"totalNamesContainingCJK":total_cjk,"startsWithCJK":starts_cjk,"noLatinBeforeFirstCJK":no_latin_before,"bad":bad}
with open(out,"w",encoding="utf-8") as f: json.dump(q,f,ensure_ascii=False,indent=2)
print(q)
