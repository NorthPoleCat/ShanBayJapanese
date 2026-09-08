#!/usr/bin/env python3
from pathlib import Path
import argparse,csv,re
ROOT=Path(__file__).resolve().parents[1]
def issues(r):
    zh=(r.get('meaning_zh') or '').strip(); out=[]
    if not zh: out.append('missing')
    if len(zh)>40: out.append('too_long')
    if re.search(r'[A-Za-z]{4,}',zh): out.append('contains_english')
    if any(x in zh for x in ['意思是','指的是','用于','表示']): out.append('looks_explanatory')
    if zh.count('；')>=5: out.append('too_many_submeanings')
    return out
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',default=str(ROOT/'data/intermediate/zh_senses.csv')); p.add_argument('--output',default=str(ROOT/'data/intermediate/zh_sense_review.csv')); a=p.parse_args()
    with Path(a.input).open('r',encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    rev=[]
    for r in rows:
        x=issues(r)
        if x: q=dict(r); q['issues']='|'.join(x); rev.append(q)
    fields=list(rows[0].keys())+['issues'] if rows else ['issues']
    with Path(a.output).open('w',encoding='utf-8-sig',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rev)
    print(f'Review rows: {len(rev):,}')
if __name__=='__main__': main()
