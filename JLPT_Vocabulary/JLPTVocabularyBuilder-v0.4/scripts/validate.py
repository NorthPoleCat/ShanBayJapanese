#!/usr/bin/env python3
from pathlib import Path
import argparse,sqlite3
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(); p.add_argument('--db',default=str(ROOT/'data/output/vocabulary.sqlite')); p.add_argument('--strict-counts',action='store_true'); a=p.parse_args(); con=sqlite3.connect(a.db)
    total=con.execute('SELECT COUNT(*) FROM vocabulary').fetchone()[0]; senses=con.execute('SELECT COUNT(*) FROM senses').fetchone()[0]; exp={5:662,4:632,3:1784,2:1793,1:3463}; ok=True
    print(f'Vocabulary: {total:,}'); print(f'Senses: {senses:,}')
    for lvl in range(5,0,-1):
        c=con.execute('SELECT COUNT(*) FROM vocabulary WHERE jlpt_level=?',(lvl,)).fetchone()[0]; print(f'N{lvl}: {c:,}'+(f' (reference {exp[lvl]:,})' if a.strict_counts else '')); ok = ok and (not a.strict_counts or c==exp[lvl])
    ew=con.execute("SELECT COUNT(*) FROM vocabulary WHERE trim(word)=''").fetchone()[0]; er=con.execute("SELECT COUNT(*) FROM vocabulary WHERE trim(reading)=''").fetchone()[0]; ns=con.execute('SELECT COUNT(*) FROM vocabulary v WHERE NOT EXISTS(SELECT 1 FROM senses s WHERE s.vocabulary_id=v.id)').fetchone()[0]; zh=con.execute("SELECT COUNT(DISTINCT vocabulary_id) FROM senses WHERE meaning_zh IS NOT NULL AND trim(meaning_zh)<>''").fetchone()[0]; integ=con.execute('PRAGMA integrity_check').fetchone()[0]; fk=con.execute('PRAGMA foreign_key_check').fetchall()
    print('Empty word:',ew); print('Empty reading:',er); print('Words without sense:',ns); print(f'Chinese sense coverage: {zh:,}/{total:,} ({(zh/total*100 if total else 0):.2f}%)'); print('SQLite integrity:',integ); print('Foreign key errors:',len(fk)); con.close()
    if ew or ns or integ!='ok' or fk or not ok: raise SystemExit(1)
if __name__=='__main__': main()
