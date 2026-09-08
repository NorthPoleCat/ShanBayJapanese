#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import argparse, csv, json, sqlite3

ROOT = Path(__file__).resolve().parents[1]

def load_zh(path):
    out = {}
    p = Path(path)
    if not p.exists(): return out
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            zh = (row.get("meaning_zh") or "").strip()
            if zh:
                out[str(row["source_seq"])] = [x.strip() for x in zh.replace("|","；").split("；") if x.strip()]
    return out

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(ROOT / "data/intermediate/matched_words.json"))
    p.add_argument("--zh", default=str(ROOT / "data/intermediate/zh_meanings.csv"))
    p.add_argument("--schema", default=str(ROOT / "schema/vocabulary.sql"))
    p.add_argument("--output", default=str(ROOT / "data/output/vocabulary.sqlite"))
    args = p.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    zh = load_zh(args.zh)
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists(): out.unlink()

    con = sqlite3.connect(out)
    con.executescript(Path(args.schema).read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()

    con.execute("INSERT INTO sources(name,url,license,retrieved_at) VALUES(?,?,?,?)",
                ("OpenJLPT","https://github.com/evanclan/OpenJLPT","CC BY-SA 4.0",now))
    sid = con.execute("SELECT id FROM sources WHERE name='OpenJLPT'").fetchone()[0]
    con.execute("INSERT INTO sources(name,url,license,retrieved_at) VALUES(?,?,?,?)",
                ("JMdict","https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project","EDRDG / verify current terms before release",now))

    for n in range(5,0,-1):
        con.execute("INSERT INTO word_lists(code,name,source) VALUES(?,?,?)",(f"JLPT_N{n}",f"JLPT N{n}","OpenJLPT"))
    list_ids = {int(code[-1]):id_ for id_,code in con.execute("SELECT id,code FROM word_lists")}

    for row in data:
        lvl = int(row["level"])
        cur = con.execute("""
          INSERT OR IGNORE INTO vocabulary
          (jmdict_entry_id,word,reading,jlpt_level,primary_pos,is_common,match_method,match_score,source_id)
          VALUES(?,?,?,?,?,?,?,?,?)
        """,(row.get("jmdict_entry_id"),row["word"],row.get("reading",""),lvl,
             " | ".join(row.get("pos",[])[:4]) or None,int(bool(row.get("is_common",False))),
             row.get("match_method"),row.get("match_score"),sid))
        if cur.rowcount:
            vid = cur.lastrowid
        else:
            vid = con.execute("SELECT id FROM vocabulary WHERE word=? AND reading=? AND jlpt_level=?",
                              (row["word"],row.get("reading",""),lvl)).fetchone()[0]
        con.execute("INSERT OR IGNORE INTO word_list_items(word_list_id,vocabulary_id,sort_order) VALUES(?,?,?)",
                    (list_ids[lvl],vid,row.get("source_seq")))

        senses = row.get("senses_en") or [row.get("meanings_en_seed",[])]
        for i,sense in enumerate(senses):
            for g in sense:
                if g:
                    con.execute("INSERT INTO meanings(vocabulary_id,language,meaning,sense_index,is_primary) VALUES(?,?,?,?,?)",
                                (vid,"en",g,i,1 if i==0 else 0))
        for i,g in enumerate(zh.get(str(row.get("source_seq")),[])):
            con.execute("INSERT INTO meanings(vocabulary_id,language,meaning,sense_index,is_primary) VALUES(?,?,?,?,?)",
                        (vid,"zh-Hans",g,i,1 if i==0 else 0))
        for ex in row.get("examples",[])[:3]:
            ja=(ex.get("ja") or "").strip(); en=(ex.get("en") or "").strip()
            if ja:
                con.execute("INSERT INTO examples(vocabulary_id,sentence_ja,sentence_en,source) VALUES(?,?,?,?)",
                            (vid,ja,en or None,"OpenJLPT"))

    for vid,word,reading in con.execute("SELECT id,word,reading FROM vocabulary"):
        zhs=[r[0] for r in con.execute("SELECT meaning FROM meanings WHERE vocabulary_id=? AND language='zh-Hans' ORDER BY sense_index",(vid,))]
        con.execute("INSERT INTO vocabulary_fts(vocabulary_id,word,reading,meaning_zh) VALUES(?,?,?,?)",
                    (vid,word,reading," ".join(zhs)))

    meta={"schema_version":"1","builder_version":"0.1.0","built_at":now,
          "word_count":str(con.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0])}
    con.executemany("INSERT INTO metadata(key,value) VALUES(?,?)",meta.items())
    con.commit(); con.execute("VACUUM"); con.close()
    print(f"SQLite -> {out}")

if __name__ == "__main__":
    main()
