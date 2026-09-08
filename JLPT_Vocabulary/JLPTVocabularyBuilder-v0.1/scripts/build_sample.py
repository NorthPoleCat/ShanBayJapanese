#!/usr/bin/env python3
from pathlib import Path
import csv, json, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
SAMPLE=[
 {"source_seq":1,"word":"食べる","reading":"たべる","level":5,"meanings_en_seed":["to eat"],"pos":["Ichidan verb"],"is_common":True,"examples":[{"ja":"毎朝パンを食べます。","en":"I eat bread every morning."}]},
 {"source_seq":2,"word":"飲む","reading":"のむ","level":5,"meanings_en_seed":["to drink"],"pos":["Godan verb"],"is_common":True},
 {"source_seq":3,"word":"見る","reading":"みる","level":5,"meanings_en_seed":["to see","to watch"],"pos":["Ichidan verb"],"is_common":True},
 {"source_seq":4,"word":"行く","reading":"いく","level":5,"meanings_en_seed":["to go"],"pos":["Godan verb"],"is_common":True},
 {"source_seq":5,"word":"学校","reading":"がっこう","level":5,"meanings_en_seed":["school"],"pos":["noun"],"is_common":True},
 {"source_seq":6,"word":"勉強","reading":"べんきょう","level":5,"meanings_en_seed":["study"],"pos":["noun","suru verb"],"is_common":True},
 {"source_seq":7,"word":"必要","reading":"ひつよう","level":4,"meanings_en_seed":["necessary","needed"],"pos":["na-adjective","noun"],"is_common":True},
 {"source_seq":8,"word":"準備","reading":"じゅんび","level":4,"meanings_en_seed":["preparation"],"pos":["noun","suru verb"],"is_common":True},
 {"source_seq":9,"word":"経験","reading":"けいけん","level":3,"meanings_en_seed":["experience"],"pos":["noun","suru verb"],"is_common":True},
 {"source_seq":10,"word":"増える","reading":"ふえる","level":3,"meanings_en_seed":["to increase"],"pos":["Ichidan verb"],"is_common":True},
 {"source_seq":11,"word":"判断","reading":"はんだん","level":2,"meanings_en_seed":["judgment","decision"],"pos":["noun","suru verb"],"is_common":True},
 {"source_seq":12,"word":"維持","reading":"いじ","level":2,"meanings_en_seed":["maintenance","preservation"],"pos":["noun","suru verb"],"is_common":True},
 {"source_seq":13,"word":"曖昧","reading":"あいまい","level":1,"meanings_en_seed":["ambiguous","vague"],"pos":["na-adjective","noun"],"is_common":True},
 {"source_seq":14,"word":"促進","reading":"そくしん","level":1,"meanings_en_seed":["promotion","acceleration"],"pos":["noun","suru verb"],"is_common":True},
 {"source_seq":15,"word":"顕著","reading":"けんちょ","level":1,"meanings_en_seed":["remarkable","notable"],"pos":["na-adjective"],"is_common":True}
]
ZH={1:"吃",2:"喝",3:"看；观看",4:"去",5:"学校",6:"学习",7:"必要；必需",8:"准备",9:"经验；经历",10:"增加；增多",11:"判断；决定",12:"维持；保持",13:"暧昧；模糊",14:"促进；推动",15:"显著；明显"}

inter=ROOT/"data/intermediate"; inter.mkdir(parents=True,exist_ok=True)
(inter/"matched_words.json").write_text(json.dumps(SAMPLE,ensure_ascii=False,indent=2),encoding="utf-8")
with (inter/"zh_meanings.csv").open("w",encoding="utf-8-sig",newline="") as f:
    fields=["source_seq","word","reading","jlpt_level","jmdict_entry_id","pos","meaning_en","meaning_zh"]
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for r in SAMPLE:
        w.writerow({"source_seq":r["source_seq"],"word":r["word"],"reading":r["reading"],
                    "jlpt_level":r["level"],"jmdict_entry_id":"","pos":" | ".join(r["pos"]),
                    "meaning_en":"；".join(r["meanings_en_seed"]),"meaning_zh":ZH[r["source_seq"]]})
subprocess.run([sys.executable,str(ROOT/"scripts/build_sqlite.py")],check=True)
subprocess.run([sys.executable,str(ROOT/"scripts/validate.py")],check=True)
