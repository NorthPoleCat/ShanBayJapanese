#!/usr/bin/env python3
from pathlib import Path
import csv,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
S=[
{'source_seq':1,'word':'食べる','reading':'たべる','level':5,'meanings_en_seed':['to eat'],'jmdict_entry_id':1358280,'readings':['たべる'],'pos':['Ichidan verb','transitive verb'],'is_common':True,'senses_en':[['to eat'],['to live on (e.g. a salary)']]},
{'source_seq':2,'word':'開く','reading':'あく','level':4,'meanings_en_seed':['to open'],'jmdict_entry_id':1000002,'readings':['あく'],'pos':['Godan verb with ku ending','intransitive verb'],'is_common':True,'senses_en':[['to open'],['to become available']]},
{'source_seq':3,'word':'開ける','reading':'あける','level':4,'meanings_en_seed':['to open'],'jmdict_entry_id':1000003,'readings':['あける'],'pos':['Ichidan verb','transitive verb'],'is_common':True,'senses_en':[['to open'],['to unwrap']]},
{'source_seq':4,'word':'静か','reading':'しずか','level':5,'meanings_en_seed':['quiet'],'jmdict_entry_id':1000004,'readings':['しずか'],'pos':['na-adjective','noun'],'is_common':True,'senses_en':[['quiet'],['peaceful']]}
]
inter=ROOT/'data/intermediate'; inter.mkdir(parents=True,exist_ok=True); (inter/'matched_words.json').write_text(json.dumps(S,ensure_ascii=False,indent=2),encoding='utf-8')
subprocess.run([sys.executable,str(ROOT/'scripts/refine_lexicon.py')],check=True); subprocess.run([sys.executable,str(ROOT/'scripts/export_sense_zh_template.py')],check=True)
p=inter/'zh_senses.csv'
with p.open('r',encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
Z={('1','0'):'吃',('1','1'):'靠……生活',('2','0'):'开；打开',('2','1'):'空出来；有空位',('3','0'):'打开',('3','1'):'拆开；解开包装',('4','0'):'安静',('4','1'):'平静；宁静'}
for r in rows: r['meaning_zh']=Z[(r['source_seq'],r['sense_index'])]; r['review_status']='approved'; r['translation_source']='sample'
with p.open('w',encoding='utf-8-sig',newline='') as f: w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
subprocess.run([sys.executable,str(ROOT/'scripts/build_sqlite.py')],check=True); subprocess.run([sys.executable,str(ROOT/'scripts/validate.py')],check=True)
