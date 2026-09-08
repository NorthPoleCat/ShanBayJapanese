#!/usr/bin/env python3
from pathlib import Path
import argparse,csv,json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',default=str(ROOT/'data/intermediate/refined_words.json')); p.add_argument('--output',default=str(ROOT/'data/intermediate/zh_senses.csv')); a=p.parse_args(); rows=json.loads(Path(a.input).read_text(encoding='utf-8'))
    fields=['source_seq','word','reading','jlpt_level','jmdict_entry_id','sense_index','pos_group','pos_text','meaning_en','meaning_zh','review_status','translation_source','translation_note']
    with Path(a.output).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows:
            for s in r.get('senses',[]): w.writerow(dict(source_seq=r.get('source_seq'),word=r.get('word',''),reading=r.get('reading',''),jlpt_level=r.get('level'),jmdict_entry_id=r.get('jmdict_entry_id',''),sense_index=s.get('sense_index',0),pos_group=r.get('pos_group',''),pos_text=s.get('pos_text',''),meaning_en=s.get('meaning_en',''),meaning_zh='',review_status='pending',translation_source='',translation_note=''))
    print('Sense translation template ->',a.output)
if __name__=='__main__': main()
