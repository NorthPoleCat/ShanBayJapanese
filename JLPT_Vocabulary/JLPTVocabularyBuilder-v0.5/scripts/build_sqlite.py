#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import argparse, csv, json, sqlite3

ROOT=Path(__file__).resolve().parents[1]

def load_sense_zh(path):
    p=Path(path)
    result={}
    if not p.exists(): return result
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            result[(str(r["source_seq"]),int(r["sense_index"]))]=r
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default=str(ROOT/"data/intermediate/enriched_words.json"))
    p.add_argument("--zh-senses",default=str(ROOT/"data/intermediate/zh_senses.csv"))
    p.add_argument("--schema",default=str(ROOT/"schema/vocabulary.sql"))
    p.add_argument("--output",default=str(ROOT/"data/output/vocabulary.sqlite"))
    args=p.parse_args()

    data=json.loads(Path(args.input).read_text(encoding="utf-8"))
    zh=load_sense_zh(args.zh_senses)

    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists(): out.unlink()

    con=sqlite3.connect(out)
    con.executescript(Path(args.schema).read_text(encoding="utf-8"))
    now=datetime.now(timezone.utc).isoformat()

    con.execute("INSERT INTO sources(name,url,license,retrieved_at) VALUES(?,?,?,?)",
                ("OpenJLPT","https://github.com/evanclan/OpenJLPT","CC BY-SA 4.0",now))
    sid=con.execute("SELECT id FROM sources WHERE name='OpenJLPT'").fetchone()[0]
    con.execute("INSERT INTO sources(name,url,license,retrieved_at) VALUES(?,?,?,?)",
                ("JMdict","https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project","Verify current EDRDG terms before release",now))

    for n in range(5,0,-1):
        con.execute("INSERT INTO word_lists(code,name,source) VALUES(?,?,?)",(f"JLPT_N{n}",f"JLPT N{n}","OpenJLPT"))
    list_ids={int(code[-1]):id_ for id_,code in con.execute("SELECT id,code FROM word_lists")}

    sense_id_map = {}

    for row in data:
        lvl=int(row["level"])
        cur=con.execute("""
          INSERT INTO vocabulary(
            jmdict_entry_id,word,reading,jlpt_level,
            primary_pos,pos_group,pos_zh,verb_class,transitivity,adjective_class,
            is_common,common_score,common_rank,
            match_method,match_score,source_id
          ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,(
            row.get("jmdict_entry_id"),row["word"],row.get("reading",""),lvl,
            row.get("primary_pos"),row.get("pos_group"),row.get("pos_zh"),
            row.get("verb_class"),row.get("transitivity"),row.get("adjective_class"),
            int(bool(row.get("is_common",False))),int(row.get("common_score",0)),
            row.get("common_rank"),row.get("match_method"),row.get("match_score"),sid
        ))
        vid=cur.lastrowid

        con.execute("INSERT INTO word_list_items(word_list_id,vocabulary_id,sort_order) VALUES(?,?,?)",
                    (list_ids[lvl],vid,row.get("source_seq")))

        for s in row.get("senses",[]):
            idx=int(s.get("sense_index",0))
            zrow=zh.get((str(row.get("source_seq")),idx),{})
            meaning_en=s.get("meaning_en","")
            meaning_zh=(zrow.get("meaning_zh") or s.get("meaning_zh") or "").strip() or None
            review=zrow.get("review_status") or s.get("review_status") or "pending"
            source=zrow.get("translation_source") or None
            note=zrow.get("translation_note") or None

            scur=con.execute("""
              INSERT INTO senses(
                vocabulary_id,jmdict_sense_index,meaning_en,meaning_zh,
                pos_text,pos_group,pos_zh,is_primary,review_status,
                translation_source,translation_note
              ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,(vid,idx,meaning_en or None,meaning_zh,
                 s.get("pos_text"),s.get("pos_group") or row.get("pos_group"),
                 s.get("pos_zh") or row.get("pos_zh"),
                 1 if idx==0 else 0,review,source,note))
            sense_id_map[(vid,idx)] = scur.lastrowid

            if meaning_en:
                con.execute("INSERT INTO meanings(vocabulary_id,language,meaning,sense_index,is_primary) VALUES(?,?,?,?,?)",
                            (vid,"en",meaning_en,idx,1 if idx==0 else 0))
            if meaning_zh:
                con.execute("INSERT INTO meanings(vocabulary_id,language,meaning,sense_index,is_primary) VALUES(?,?,?,?,?)",
                            (vid,"zh-Hans",meaning_zh,idx,1 if idx==0 else 0))

        for ex in row.get("examples",[])[:3]:
            ja=(ex.get("ja") or "").strip()
            en=(ex.get("en") or "").strip()
            if not ja: continue
            sidx=ex.get("sense_index")
            sid2=sense_id_map.get((vid,int(sidx))) if sidx is not None else None
            con.execute("""
              INSERT INTO examples(
                vocabulary_id,sense_id,sentence_ja,sentence_en,source,
                sense_match_method,sense_match_score
              ) VALUES(?,?,?,?,?,?,?)
            """,(vid,sid2,ja,en or None,"OpenJLPT",
                 ex.get("sense_match_method"),ex.get("sense_match_score")))

        df=row.get("distractor_features") or {}
        con.execute("""
          INSERT INTO distractor_features(
            vocabulary_id,same_level,pos_group,pos_zh,reading_length,mora_bucket,
            script_type,has_kanji,first_char,last_char,meaning_keywords,
            sense_count,common_score
          ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,(vid,lvl,df.get("pos_group"),df.get("pos_zh"),
             df.get("reading_length"),df.get("mora_bucket"),df.get("script_type"),
             int(df.get("has_kanji",0)),df.get("first_char"),df.get("last_char"),
             df.get("meaning_keywords"),df.get("sense_count",0),df.get("common_score",0)))

    for vid,word,reading in con.execute("SELECT id,word,reading FROM vocabulary"):
        zh_text=" ".join(x[0] for x in con.execute(
            "SELECT COALESCE(meaning_zh,'') FROM senses WHERE vocabulary_id=? ORDER BY jmdict_sense_index",(vid,)))
        en_text=" ".join(x[0] for x in con.execute(
            "SELECT COALESCE(meaning_en,'') FROM senses WHERE vocabulary_id=? ORDER BY jmdict_sense_index",(vid,)))
        con.execute("INSERT INTO vocabulary_fts(vocabulary_id,word,reading,meaning_zh,meaning_en) VALUES(?,?,?,?,?)",
                    (vid,word,reading,zh_text,en_text))

    meta={
        "schema_version":"3",
        "builder_version":"0.5.0",
        "built_at":now,
        "word_count":str(con.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]),
        "sense_count":str(con.execute("SELECT COUNT(*) FROM senses").fetchone()[0]),
        "example_bound_count":str(con.execute("SELECT COUNT(*) FROM examples WHERE sense_id IS NOT NULL").fetchone()[0])
    }
    con.executemany("INSERT INTO metadata(key,value) VALUES(?,?)",meta.items())
    con.commit(); con.execute("VACUUM"); con.close()
    print(f"SQLite -> {out}")

if __name__=="__main__":
    main()
