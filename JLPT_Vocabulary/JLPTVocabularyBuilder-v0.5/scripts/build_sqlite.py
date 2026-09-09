#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import argparse, csv, json, re, sqlite3

ROOT=Path(__file__).resolve().parents[1]

PRIORITY_WEIGHTS = {
    "ichi1": 100, "news1": 90, "spec1": 80, "gai1": 70,
    "ichi2": 50, "news2": 40, "spec2": 30, "gai2": 20,
}

def priority_score(tags):
    score = 0
    for tag in filter(None, (tags or "").split(",")):
        score += PRIORITY_WEIGHTS.get(tag, 0)
        if tag.startswith("nf") and tag[2:].isdigit():
            score += max(1, 51-int(tag[2:]))
    return score

def spelling_type(value):
    has_kanji = bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", value))
    has_kana = bool(re.search(r"[\u3040-\u30ff]", value))
    if has_kanji and has_kana: return "mixed"
    if has_kanji: return "kanji"
    return "kana"

def load_spellings(index, row):
    source_word=(row.get("word") or "").strip()
    source_reading=(row.get("reading") or "").strip()
    candidates={}

    def add(value, kind=None, tags=""):
        value=(value or "").strip()
        if not value: return
        current=candidates.get(value)
        new_tags=",".join(dict.fromkeys(filter(None,(tags or "").split(","))))
        new_score=priority_score(new_tags)
        if current is None or new_score > current[2]:
            candidates[value]=(kind or spelling_type(value),new_tags,new_score)

    entry_id=row.get("jmdict_entry_id")
    if index is not None and entry_id:
        for value,tags in index.execute("SELECT keb, COALESCE(priority,'') FROM kanji WHERE ent_seq=?",(entry_id,)):
            add(value,"kanji" if spelling_type(value)=="kanji" else "mixed",tags)
        for value,tags in index.execute("SELECT reb, COALESCE(priority,'') FROM reading WHERE ent_seq=?",(entry_id,)):
            add(value,"kana",tags)
    add(source_word)
    add(source_reading,"kana")

    # JMdict's ke_pri tags describe preferred written forms. Use the strongest
    # tagged kanji form; otherwise preserve the spelling supplied by OpenJLPT.
    kanji_candidates=[(value,*details) for value,details in candidates.items()
                      if details[0] in ("kanji","mixed") and details[2] > 0]
    if kanji_candidates:
        primary=max(kanji_candidates,key=lambda item:(item[3],item[0]==source_word,-len(item[0])))[0]
    elif source_word in candidates:
        primary=source_word
    elif candidates:
        primary=next(iter(candidates))
    else:
        return []

    return sorted(
        [(value,kind,tags,score,int(value==primary)) for value,(kind,tags,score) in candidates.items()],
        key=lambda item:(-item[4],-item[3],item[1]=="kana",item[0])
    )

def load_sense_zh(path):
    p=Path(path)
    result={}
    if not p.exists(): return result
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            result[(str(r["source_seq"]),int(r["sense_index"]))]=r
    return result

def load_example_zh(path):
    p=Path(path)
    result={}
    if not p.exists(): return result
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            key=((r.get("sentence_ja") or "").strip(),(r.get("sentence_en") or "").strip())
            result[key]=(r.get("sentence_zh") or "").strip()
    return result

def extract_meaning_keywords(meanings):
    parts = re.split(r"[；，、,/（）()：:\s]+", "；".join(meanings))
    seen = []
    for part in parts:
        value = part.strip()
        if 1 <= len(value) <= 12 and value not in seen:
            seen.append(value)
    return "|".join(seen[:12])

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default=str(ROOT/"data/intermediate/enriched_words.json"))
    p.add_argument("--zh-senses",default=str(ROOT/"data/intermediate/zh_senses.csv"))
    p.add_argument("--zh-examples",default=str(ROOT/"data/intermediate/zh_examples.csv"))
    p.add_argument("--jmdict-index",default=str(ROOT/"data/intermediate/jmdict_index.sqlite"))
    p.add_argument("--schema",default=str(ROOT/"schema/vocabulary.sql"))
    p.add_argument("--output",default=str(ROOT/"data/output/vocabulary.sqlite"))
    args=p.parse_args()

    data=json.loads(Path(args.input).read_text(encoding="utf-8"))
    zh=load_sense_zh(args.zh_senses)
    example_zh=load_example_zh(args.zh_examples)
    index_path=Path(args.jmdict_index)
    jmdict_index=sqlite3.connect(index_path) if index_path.exists() else None

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

        for spelling,kind,tags,score,is_primary in load_spellings(jmdict_index,row):
            con.execute("""
              INSERT INTO vocabulary_spellings(
                vocabulary_id,spelling,spelling_type,priority_tags,priority_score,is_primary
              ) VALUES(?,?,?,?,?,?)
            """,(vid,spelling,kind,tags or None,score,is_primary))

        con.execute("INSERT INTO word_list_items(word_list_id,vocabulary_id,sort_order) VALUES(?,?,?)",
                    (list_ids[lvl],vid,row.get("source_seq")))

        row_meanings_zh = []
        for s in row.get("senses",[]):
            idx=int(s.get("sense_index",0))
            zrow=zh.get((str(row.get("source_seq")),idx),{})
            meaning_en=s.get("meaning_en","")
            meaning_zh=(zrow.get("meaning_zh") or s.get("meaning_zh") or "").strip() or None
            review=zrow.get("review_status") or s.get("review_status") or "pending"
            source=zrow.get("translation_source") or None
            note=zrow.get("translation_note") or None
            if meaning_zh:
                row_meanings_zh.append(meaning_zh)

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
            zh_sentence=example_zh.get((ja,en)) or None
            if not ja: continue
            sidx=ex.get("sense_index")
            sid2=sense_id_map.get((vid,int(sidx))) if sidx is not None else None
            con.execute("""
              INSERT INTO examples(
                vocabulary_id,sense_id,sentence_ja,sentence_zh,sentence_en,source,
                sense_match_method,sense_match_score
              ) VALUES(?,?,?,?,?,?,?,?)
            """,(vid,sid2,ja,zh_sentence,en or None,"OpenJLPT",
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
             df.get("meaning_keywords") or extract_meaning_keywords(row_meanings_zh),
             df.get("sense_count",0),df.get("common_score",0)))

    for vid,word,reading in con.execute("SELECT id,word,reading FROM vocabulary"):
        searchable_spellings=" ".join(x[0] for x in con.execute(
            "SELECT spelling FROM vocabulary_spellings WHERE vocabulary_id=? ORDER BY is_primary DESC, priority_score DESC",(vid,)))
        zh_text=" ".join(x[0] for x in con.execute(
            "SELECT COALESCE(meaning_zh,'') FROM senses WHERE vocabulary_id=? ORDER BY jmdict_sense_index",(vid,)))
        en_text=" ".join(x[0] for x in con.execute(
            "SELECT COALESCE(meaning_en,'') FROM senses WHERE vocabulary_id=? ORDER BY jmdict_sense_index",(vid,)))
        con.execute("INSERT INTO vocabulary_fts(vocabulary_id,word,reading,meaning_zh,meaning_en) VALUES(?,?,?,?,?)",
                    (vid,searchable_spellings or word,reading,zh_text,en_text))

    meta={
        "schema_version":"4",
        "builder_version":"0.5.1",
        "built_at":now,
        "word_count":str(con.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]),
        "sense_count":str(con.execute("SELECT COUNT(*) FROM senses").fetchone()[0]),
        "spelling_count":str(con.execute("SELECT COUNT(*) FROM vocabulary_spellings").fetchone()[0]),
        "example_zh_count":str(con.execute("SELECT COUNT(*) FROM examples WHERE sentence_zh IS NOT NULL AND trim(sentence_zh)<>''").fetchone()[0]),
        "example_bound_count":str(con.execute("SELECT COUNT(*) FROM examples WHERE sense_id IS NOT NULL").fetchone()[0])
    }
    con.executemany("INSERT INTO metadata(key,value) VALUES(?,?)",meta.items())
    con.commit(); con.execute("VACUUM"); con.close()
    if jmdict_index is not None: jmdict_index.close()
    print(f"SQLite -> {out}")

if __name__=="__main__":
    main()
