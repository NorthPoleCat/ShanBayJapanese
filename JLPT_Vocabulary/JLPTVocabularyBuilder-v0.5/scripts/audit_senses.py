#!/usr/bin/env python3
from pathlib import Path
import argparse, csv, re

ROOT = Path(__file__).resolve().parents[1]

def issues(row):
    zh=(row.get("meaning_zh") or "").strip()
    out=[]
    if not zh: out.append("missing")
    if len(zh) > 40: out.append("too_long")
    if re.search(r"[A-Za-z]{4,}", zh): out.append("contains_english")
    if any(x in zh for x in ["意思是","指的是","用于","表示"]): out.append("looks_explanatory")
    if zh.count("；") >= 5: out.append("too_many_submeanings")
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default=str(ROOT/"data/intermediate/zh_senses.csv"))
    p.add_argument("--output",default=str(ROOT/"data/intermediate/zh_sense_review.csv"))
    args=p.parse_args()

    with Path(args.input).open("r",encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))

    review=[]
    for r in rows:
        xs=issues(r)
        if xs:
            rr=dict(r)
            rr["issues"]="|".join(xs)
            review.append(rr)

    fields=list(rows[0].keys())+["issues"] if rows else ["issues"]
    with Path(args.output).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        w.writerows(review)

    print(f"Review rows: {len(review):,}")
    print(f"Output: {args.output}")

if __name__=="__main__":
    main()
