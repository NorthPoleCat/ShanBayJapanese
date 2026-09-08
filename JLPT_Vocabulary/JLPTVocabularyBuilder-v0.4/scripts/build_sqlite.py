#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,json,sqlite3
ROOT=Path(__file__).resolve().parents[1]
def loadzh(path):
    d={}; p=Path(path)
    if not p.exists(): return d
    with p.open('r',encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f): d[(str(r['source_seq']),int(r['sense_index']))]=r
    return d

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',default=str(ROOT/'data/intermediate/refined_words.json')); p.add_argument('--zh-senses',default=str(ROOT/'data/intermediate/zh_senses.csv')); p.add_argument('--schema',default=str(ROOT/'schema/vocabulary.sql')); p.add_argument('--output',default=str(ROOT/'data/output/vocabulary.sqlite')); a=p.parse_args()
    data=json.loads(Path(a.input).read_text(encoding='utf-8')); zh=loadzh(a.zh_senses); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists(): out.unlink()
    con=sqlite3.connect(out); con.executescript(Path(a.schema).read_text(encoding='utf-8')); now=datetime.now(timezone.utc).isoformat()
    con.execute('INSERT INTO sources(name,url,license,retrieved_at) VALUES(?,?,?,?)',('OpenJLPT','https://github.com/evanclan/OpenJLPT','CC BY-SA 4.0',now)); sid=con.execute("SELECT id FROM sources WHERE name='OpenJLPT'").fetchone()[0]
    con.execute('INSERT INTO sources(name,url,license,retrieved_at) VALUES(?,?,?,?)',('JMdict','https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project','Verify current EDRDG terms before release',now))
    for n in range(5,0,-1): con.execute('INSERT INTO word_lists(code,name,source) VALUES(?,?,?)',(f'JLPT_N{n}',f'JLPT N{n}','OpenJLPT'))
    lids={int(code[-1]):i for i,code in con.execute('SELECT id,code FROM word_lists')}
    for r in data:
        lvl=int(r['level'])
        cur=con.execute('INSERT INTO vocabulary(jmdict_entry_id,word,reading,jlpt_level,primary_pos,pos_group,verb_class,transitivity,adjective_class,is_common,match_method,match_score,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(r.get('jmdict_entry_id'),r['word'],r.get('reading',''),lvl,r.get('primary_pos'),r.get('pos_group'),r.get('verb_class'),r.get('transitivity'),r.get('adjective_class'),int(bool(r.get('is_common',False))),r.get('match_method'),r.get('match_score'),sid)); vid=cur.lastrowid
        con.execute('INSERT INTO word_list_items(word_list_id,vocabulary_id,sort_order) VALUES(?,?,?)',(lids[lvl],vid,r.get('source_seq')))
        for s in r.get('senses',[]):
            idx=int(s.get('sense_index',0)); z=zh.get((str(r.get('source_seq')),idx),{}); en=s.get('meaning_en') or None; cz=(z.get('meaning_zh') or '').strip() or None
            con.execute('INSERT INTO senses(vocabulary_id,jmdict_sense_index,meaning_en,meaning_zh,pos_text,pos_group,is_primary,review_status,translation_source,translation_note) VALUES(?,?,?,?,?,?,?,?,?,?)',(vid,idx,en,cz,s.get('pos_text'),r.get('pos_group'),1 if idx==0 else 0,z.get('review_status') or 'pending',z.get('translation_source') or None,z.get('translation_note') or None))
            if en: con.execute('INSERT INTO meanings(vocabulary_id,language,meaning,sense_index,is_primary) VALUES(?,?,?,?,?)',(vid,'en',en,idx,1 if idx==0 else 0))
            if cz: con.execute('INSERT INTO meanings(vocabulary_id,language,meaning,sense_index,is_primary) VALUES(?,?,?,?,?)',(vid,'zh-Hans',cz,idx,1 if idx==0 else 0))
        for ex in r.get('examples',[])[:3]:
            ja=(ex.get('ja') or '').strip(); en=(ex.get('en') or '').strip()
            if ja: con.execute('INSERT INTO examples(vocabulary_id,sentence_ja,sentence_en,source) VALUES(?,?,?,?)',(vid,ja,en or None,'OpenJLPT'))
    for vid,word,reading in con.execute('SELECT id,word,reading FROM vocabulary'):
        z=' '.join(x[0] for x in con.execute("SELECT COALESCE(meaning_zh,'') FROM senses WHERE vocabulary_id=? ORDER BY jmdict_sense_index",(vid,)))
        e=' '.join(x[0] for x in con.execute("SELECT COALESCE(meaning_en,'') FROM senses WHERE vocabulary_id=? ORDER BY jmdict_sense_index",(vid,)))
        con.execute('INSERT INTO vocabulary_fts(vocabulary_id,word,reading,meaning_zh,meaning_en) VALUES(?,?,?,?,?)',(vid,word,reading,z,e))
    meta={'schema_version':'2','builder_version':'0.4.0','built_at':now,'word_count':str(con.execute('SELECT COUNT(*) FROM vocabulary').fetchone()[0]),'sense_count':str(con.execute('SELECT COUNT(*) FROM senses').fetchone()[0])}
    con.executemany('INSERT INTO metadata(key,value) VALUES(?,?)',meta.items()); con.commit(); con.execute('VACUUM'); con.close(); print('SQLite ->',out)
if __name__=='__main__': main()
