#!/usr/bin/env python3
from pathlib import Path
import argparse, sqlite3

ROOT = Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",default=str(ROOT/"data/output/vocabulary.sqlite"))
    p.add_argument("--strict-counts",action="store_true")
    args=p.parse_args()
    con=sqlite3.connect(args.db)
    total=con.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
    expected={5:662,4:632,3:1784,2:1793,1:3463}
    ok=True
    print(f"Vocabulary: {total:,}")
    for lvl in range(5,0,-1):
        count=con.execute("SELECT COUNT(*) FROM vocabulary WHERE jlpt_level=?",(lvl,)).fetchone()[0]
        print(f"N{lvl}: {count:,}" + (f" (reference {expected[lvl]:,})" if args.strict_counts else ""))
        if args.strict_counts and count!=expected[lvl]: ok=False
    empty=con.execute("SELECT COUNT(*) FROM vocabulary WHERE trim(word)=''").fetchone()[0]
    dup=con.execute("""SELECT COUNT(*) FROM (
      SELECT word,reading,jlpt_level,COUNT(*) c FROM vocabulary
      GROUP BY word,reading,jlpt_level HAVING c>1)""").fetchone()[0]
    unmatched=con.execute("SELECT COUNT(*) FROM vocabulary WHERE jmdict_entry_id IS NULL").fetchone()[0]
    zh=con.execute("SELECT COUNT(DISTINCT vocabulary_id) FROM meanings WHERE language='zh-Hans'").fetchone()[0]
    integ=con.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"Empty words: {empty}")
    print(f"Duplicate word+reading+level: {dup}")
    print(f"No JMdict match: {unmatched:,}")
    print(f"Chinese coverage: {zh:,}/{total:,} ({(zh/total*100 if total else 0):.2f}%)")
    print(f"SQLite integrity: {integ}")
    con.close()
    if empty or dup or integ!="ok" or not ok: raise SystemExit(1)

if __name__=="__main__":
    main()
