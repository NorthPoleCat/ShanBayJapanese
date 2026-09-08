#!/usr/bin/env python3
from pathlib import Path
import argparse, csv, json

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(ROOT / "data/intermediate/matched_words.json"))
    p.add_argument("--output", default=str(ROOT / "data/intermediate/zh_meanings.csv"))
    args = p.parse_args()
    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))

    with Path(args.output).open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["source_seq","word","reading","jlpt_level","jmdict_entry_id","pos","meaning_en","meaning_zh"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows:
            senses = r.get("senses_en") or [r.get("meanings_en_seed", [])]
            w.writerow({
                "source_seq": r.get("source_seq"),
                "word": r.get("word",""),
                "reading": r.get("reading",""),
                "jlpt_level": r.get("level"),
                "jmdict_entry_id": r.get("jmdict_entry_id",""),
                "pos": " | ".join(r.get("pos",[])),
                "meaning_en": "；".join(g for s in senses for g in s),
                "meaning_zh": ""
            })
    print(f"Chinese meaning template -> {args.output}")

if __name__ == "__main__":
    main()
