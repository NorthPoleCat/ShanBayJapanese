#!/usr/bin/env python3
from pathlib import Path
import argparse, csv, math

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',default=str(ROOT/'data/intermediate/zh_meanings.csv'))
    p.add_argument('--batch-size',type=int,default=20)
    args=p.parse_args()
    with Path(args.input).open('r',encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    pending=[r for r in rows if not (r.get('meaning_zh') or '').strip()]
    chars=sum(len((r.get('word') or '')+(r.get('reading') or '')+(r.get('pos') or '')+(r.get('meaning_en') or '')) for r in pending)
    rough_input_tokens=int(chars/2.5)+len(pending)*25
    rough_output_tokens=len(pending)*18
    print(f'Pending words: {len(pending):,}')
    print(f'Batches (@{args.batch_size}): {math.ceil(len(pending)/args.batch_size):,}')
    print(f'Rough input tokens: {rough_input_tokens:,}')
    print(f'Rough output tokens: {rough_output_tokens:,}')
    print('These are planning estimates only; actual tokenization depends on model and prompt.')

if __name__=='__main__': main()
