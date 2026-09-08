#!/usr/bin/env python3
from pathlib import Path
import argparse, csv, json, re

ROOT = Path(__file__).resolve().parents[1]

ASCII_WORD = re.compile(r'[A-Za-z]{3,}')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',default=str(ROOT/'data/intermediate/zh_meanings.csv'))
    p.add_argument('--output',default=str(ROOT/'data/intermediate/zh_review.csv'))
    args=p.parse_args()

    with Path(args.input).open('r',encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))

    review=[]
    for r in rows:
        zh=(r.get('meaning_zh') or '').strip()
        reasons=[]
        if not zh:
            reasons.append('missing')
        parts=[x.strip() for x in zh.split('；') if x.strip()]
        if len(parts)>6:
            reasons.append('too_many_senses')
        if any(len(x)>24 for x in parts):
            reasons.append('sense_too_long')
        if ASCII_WORD.search(zh):
            reasons.append('contains_english')
        if any(x.endswith(('。','！','？')) for x in parts):
            reasons.append('looks_like_sentence')
        if reasons:
            rr=dict(r); rr['review_reason']='|'.join(reasons); review.append(rr)

    fields=list(rows[0].keys())+['review_reason'] if rows else ['review_reason']
    with Path(args.output).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(review)
    print(f'Review queue: {len(review):,}/{len(rows):,} -> {args.output}')

if __name__=='__main__':
    main()
