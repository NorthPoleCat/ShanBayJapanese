#!/usr/bin/env python3
from pathlib import Path
import argparse, gzip, sqlite3, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

DDL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS entry(ent_seq INTEGER PRIMARY KEY,is_common INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS kanji(ent_seq INTEGER NOT NULL,keb TEXT NOT NULL,priority TEXT);
CREATE INDEX IF NOT EXISTS idx_kanji_keb ON kanji(keb);
CREATE TABLE IF NOT EXISTS reading(ent_seq INTEGER NOT NULL,reb TEXT NOT NULL,no_kanji INTEGER NOT NULL DEFAULT 0,restrictions TEXT,priority TEXT);
CREATE INDEX IF NOT EXISTS idx_reading_reb ON reading(reb);
CREATE TABLE IF NOT EXISTS sense(ent_seq INTEGER NOT NULL,sense_index INTEGER NOT NULL,pos TEXT,gloss_en TEXT,PRIMARY KEY(ent_seq,sense_index));
"""

def text_list(parent, tag):
    return [(e.text or "").strip() for e in parent.findall(tag) if (e.text or "").strip()]

def parse(xml_gz: Path, out_db: Path):
    if out_db.exists():
        out_db.unlink()
    con = sqlite3.connect(out_db)
    con.executescript(DDL)
    count = 0

    with gzip.open(xml_gz, "rb") as fh:
        for _, elem in ET.iterparse(fh, events=("end",)):
            if elem.tag != "entry":
                continue
            ent_seq = int(elem.findtext("ent_seq"))
            common = 0
            k_rows, r_rows, s_rows = [], [], []

            for ke in elem.findall("k_ele"):
                keb = (ke.findtext("keb") or "").strip()
                pri = text_list(ke, "ke_pri")
                common |= bool(pri)
                if keb:
                    k_rows.append((ent_seq, keb, ",".join(pri)))

            for re in elem.findall("r_ele"):
                reb = (re.findtext("reb") or "").strip()
                pri = text_list(re, "re_pri")
                common |= bool(pri)
                restr = text_list(re, "re_restr")
                no_kanji = 1 if re.find("re_nokanji") is not None else 0
                if reb:
                    r_rows.append((ent_seq, reb, no_kanji, ",".join(restr), ",".join(pri)))

            for idx, sense in enumerate(elem.findall("sense")):
                pos = text_list(sense, "pos")
                glosses = []
                for g in sense.findall("gloss"):
                    lang = g.attrib.get(XML_LANG, "eng")
                    if lang in ("eng", "en", "") and (g.text or "").strip():
                        glosses.append((g.text or "").strip())
                s_rows.append((ent_seq, idx, "|".join(pos), "|".join(glosses)))

            con.execute("INSERT INTO entry(ent_seq,is_common) VALUES(?,?)", (ent_seq, int(bool(common))))
            con.executemany("INSERT INTO kanji(ent_seq,keb,priority) VALUES(?,?,?)", k_rows)
            con.executemany("INSERT INTO reading(ent_seq,reb,no_kanji,restrictions,priority) VALUES(?,?,?,?,?)", r_rows)
            con.executemany("INSERT INTO sense(ent_seq,sense_index,pos,gloss_en) VALUES(?,?,?,?)", s_rows)

            count += 1
            if count % 5000 == 0:
                con.commit()
                print(f"Parsed {count:,} JMdict entries...")
            elem.clear()

    con.commit()
    con.execute("ANALYZE")
    con.close()
    print(f"JMdict index -> {out_db}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(ROOT / "data/raw/jmdict/JMdict_e.gz"))
    p.add_argument("--output", default=str(ROOT / "data/intermediate/jmdict_index.sqlite"))
    args = p.parse_args()
    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run download_sources.py first.")
    parse(path, Path(args.output))

if __name__ == "__main__":
    main()
