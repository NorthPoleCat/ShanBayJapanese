#!/usr/bin/env python3
from pathlib import Path
import argparse, sqlite3
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",default=str(ROOT/"data/output/vocabulary.sqlite"))
    p.add_argument("--strict-counts",action="store_true")
    args=p.parse_args()

    con=sqlite3.connect(args.db)
    total=con.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
    senses=con.execute("SELECT COUNT(*) FROM senses").fetchone()[0]
    examples=con.execute("SELECT COUNT(*) FROM examples").fetchone()[0]
    examples_zh=con.execute("SELECT COUNT(*) FROM examples WHERE sentence_zh IS NOT NULL AND trim(sentence_zh)<>''").fetchone()[0]
    bound=con.execute("SELECT COUNT(*) FROM examples WHERE sense_id IS NOT NULL").fetchone()[0]
    poszh=con.execute("SELECT COUNT(*) FROM vocabulary WHERE pos_zh IS NOT NULL AND trim(pos_zh)<>''").fetchone()[0]
    distract=con.execute("SELECT COUNT(*) FROM distractor_features").fetchone()[0]
    expected={5:662,4:632,3:1784,2:1793,1:3463}
    ok=True

    print(f"Vocabulary: {total:,}")
    print(f"Senses: {senses:,}")
    print(f"Examples: {examples:,}")
    print(f"Chinese example coverage: {examples_zh:,}/{examples:,}")
    print(f"Examples bound to sense: {bound:,}/{examples:,}")
    print(f"POS Chinese coverage: {poszh:,}/{total:,}")
    print(f"Distractor feature rows: {distract:,}/{total:,}")

    for lvl in range(5,0,-1):
        count=con.execute("SELECT COUNT(*) FROM vocabulary WHERE jlpt_level=?",(lvl,)).fetchone()[0]
        print(f"N{lvl}: {count:,}" + (f" (reference {expected[lvl]:,})" if args.strict_counts else ""))
        if args.strict_counts and count!=expected[lvl]: ok=False

    empty_word=con.execute("SELECT COUNT(*) FROM vocabulary WHERE trim(word)=''").fetchone()[0]
    empty_reading=con.execute("SELECT COUNT(*) FROM vocabulary WHERE trim(reading)=''").fetchone()[0]
    no_sense=con.execute("""
      SELECT COUNT(*) FROM vocabulary v
      WHERE NOT EXISTS(SELECT 1 FROM senses s WHERE s.vocabulary_id=v.id)
    """).fetchone()[0]
    zh_cov=con.execute("""
      SELECT COUNT(DISTINCT vocabulary_id)
      FROM senses
      WHERE meaning_zh IS NOT NULL AND trim(meaning_zh)<>''
    """).fetchone()[0]
    integrity=con.execute("PRAGMA integrity_check").fetchone()[0]
    fk=con.execute("PRAGMA foreign_key_check").fetchall()

    print(f"Empty word: {empty_word}")
    print(f"Empty reading: {empty_reading}")
    print(f"Words without sense: {no_sense}")
    print(f"Chinese sense coverage: {zh_cov:,}/{total:,} ({(zh_cov/total*100 if total else 0):.2f}%)")
    print(f"SQLite integrity: {integrity}")
    print(f"Foreign key errors: {len(fk)}")

    if poszh != total or distract != total:
        ok=False
    if empty_word or no_sense or integrity!="ok" or fk:
        ok=False
    if examples_zh != examples:
        ok=False
    con.close()
    if not ok: raise SystemExit(1)

if __name__=="__main__":
    main()
