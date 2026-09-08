#!/usr/bin/env python3
from pathlib import Path
import csv, json, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
SAMPLE=[
 {
  "source_seq":1,"word":"食べる","reading":"たべる","level":5,
  "meanings_en_seed":["to eat"],"jmdict_entry_id":1358280,
  "readings":["たべる"],"pos":["Ichidan verb","transitive verb"],"primary_pos":"Ichidan verb",
  "pos_group":"verb","verb_class":"ichidan","transitivity":"transitive",
  "adjective_class":None,"is_common":True,"priority_tags":["ichi1","news1"],
  "senses_en":[["to eat"],["to live on (e.g. a salary)"]],
  "examples":[
    {"ja":"毎朝パンを食べます。","en":"I eat bread every morning."},
    {"ja":"この給料で食べている。","en":"I live on this salary."}
  ]
 },
 {
  "source_seq":2,"word":"開く","reading":"あく","level":4,
  "meanings_en_seed":["to open"],"jmdict_entry_id":1000002,
  "readings":["あく"],"pos":["Godan verb with ku ending","intransitive verb"],"primary_pos":"Godan verb with ku ending",
  "pos_group":"verb","verb_class":"godan","transitivity":"intransitive",
  "adjective_class":None,"is_common":True,"priority_tags":["ichi1"],
  "senses_en":[["to open"],["to become available"]],
  "examples":[{"ja":"店が九時に開く。","en":"The shop opens at nine."}]
 },
 {
  "source_seq":3,"word":"静か","reading":"しずか","level":5,
  "meanings_en_seed":["quiet"],"jmdict_entry_id":1000003,
  "readings":["しずか"],"pos":["na-adjective","noun"],"primary_pos":"na-adjective",
  "pos_group":"adjective","verb_class":None,"transitivity":"unknown",
  "adjective_class":"na","is_common":False,"priority_tags":[],
  "senses_en":[["quiet"],["peaceful"]],
  "examples":[{"ja":"この町はとても静かです。","en":"This town is very quiet."}]
 }
]

inter=ROOT/"data/intermediate"; inter.mkdir(parents=True,exist_ok=True)
(inter/"matched_words.json").write_text(json.dumps(SAMPLE,ensure_ascii=False,indent=2),encoding="utf-8")

subprocess.run([sys.executable,str(ROOT/"scripts/refine_lexicon.py")],check=True)
subprocess.run([sys.executable,str(ROOT/"scripts/export_sense_zh_template.py")],check=True)

rows=[]
path=inter/"zh_senses.csv"
with path.open("r",encoding="utf-8-sig",newline="") as f:
    rows=list(csv.DictReader(f))
zh_map={
 ("1","0"):"吃",("1","1"):"靠……生活",
 ("2","0"):"开；打开",("2","1"):"空出来；有空位",
 ("3","0"):"安静",("3","1"):"平静；宁静",
}
for r in rows:
    r["meaning_zh"]=zh_map[(r["source_seq"],r["sense_index"])]
    r["review_status"]="approved"
    r["translation_source"]="sample"
with path.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

# Put zh values back into refined words too, so enrich_learning_data can derive semantic keywords.
refined=json.loads((inter/"refined_words.json").read_text(encoding="utf-8"))
for rr in refined:
    for s in rr["senses"]:
        s["meaning_zh"]=zh_map[(str(rr["source_seq"]),str(s["sense_index"]))]
(inter/"refined_words.json").write_text(json.dumps(refined,ensure_ascii=False,indent=2),encoding="utf-8")

subprocess.run([sys.executable,str(ROOT/"scripts/enrich_learning_data.py")],check=True)
subprocess.run([sys.executable,str(ROOT/"scripts/build_sqlite.py")],check=True)
subprocess.run([sys.executable,str(ROOT/"scripts/validate.py")],check=True)
