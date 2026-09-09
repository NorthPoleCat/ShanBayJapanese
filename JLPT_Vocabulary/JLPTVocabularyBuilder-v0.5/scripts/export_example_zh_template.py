#!/usr/bin/env python3
from pathlib import Path
import argparse, csv, json

ROOT = Path(__file__).resolve().parents[1]

def load_existing(path):
    if not path.exists(): return {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {((r.get("sentence_ja") or "").strip(), (r.get("sentence_en") or "").strip()): r for r in csv.DictReader(f)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default=str(ROOT/"data/intermediate/enriched_words.json"))
    p.add_argument("--output",default=str(ROOT/"data/intermediate/zh_examples.csv"))
    args=p.parse_args()
    rows=json.loads(Path(args.input).read_text(encoding="utf-8")); out=Path(args.output)
    existing=load_existing(out); unique={}
    for row in rows:
        for ex in (row.get("examples") or [])[:3]:
            ja=(ex.get("ja") or "").strip(); en=(ex.get("en") or "").strip()
            if ja: unique.setdefault((ja,en),(row.get("source_seq"),row.get("word","")))
    fields=["example_id","source_seq","word","sentence_ja","sentence_en","sentence_zh","review_status","translation_source","translation_note"]
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for eid,((ja,en),(seq,word)) in enumerate(unique.items(),1):
            old=existing.get((ja,en),{})
            w.writerow({"example_id":eid,"source_seq":seq,"word":word,"sentence_ja":ja,"sentence_en":en,
                        "sentence_zh":old.get("sentence_zh",""),"review_status":old.get("review_status","pending"),
                        "translation_source":old.get("translation_source",""),"translation_note":old.get("translation_note","")})
    print(f"Unique example translation template: {len(unique):,} -> {out}")

if __name__=="__main__": main()
