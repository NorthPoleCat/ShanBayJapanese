#!/usr/bin/env python3
from pathlib import Path
import argparse,csv,re
ROOT=Path(__file__).resolve().parents[1]
def issues(r):
    zh=(r.get("sentence_zh") or "").strip(); out=[]
    if not zh: out.append("missing")
    if len(zh)>80: out.append("too_long")
    if zh==(r.get("sentence_en") or "").strip(): out.append("same_as_english")
    if re.search(r"\b(the|and|you|this|that|with|from)\b",zh,re.I): out.append("contains_english")
    return out
def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",default=str(ROOT/"data/intermediate/zh_examples.csv")); p.add_argument("--output",default=str(ROOT/"data/intermediate/zh_example_review.csv")); args=p.parse_args()
    with Path(args.input).open("r",encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    review=[dict(r,issues="|".join(xs)) for r in rows if (xs:=issues(r))]
    fields=list(rows[0].keys())+["issues"] if rows else ["issues"]
    with Path(args.output).open("w",encoding="utf-8-sig",newline="") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(review)
    print(f"Example review rows: {len(review):,}"); print(f"Output: {args.output}")
if __name__=="__main__": main()
