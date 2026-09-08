#!/usr/bin/env python3
from pathlib import Path
import json, argparse, re, unicodedata

ROOT = Path(__file__).resolve().parents[1]

def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())

def kana_only(s: str) -> bool:
    if not s:
        return False
    return all(("\u3040" <= c <= "\u30ff") or c in "ー・ " for c in s)

def variants(word: str):
    parts = [norm(x) for x in re.split(r"[/／]", word) if norm(x)]
    return parts or [norm(word)]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default=str(ROOT / "data/raw/openjlpt"))
    p.add_argument("--output", default=str(ROOT / "data/intermediate/jlpt_words.json"))
    args = p.parse_args()

    rows, seq = [], 0
    for n in range(5, 0, -1):
        path = Path(args.input_dir) / f"n{n}.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}. Run download_sources.py first.")
        for item in json.loads(path.read_text(encoding="utf-8")):
            seq += 1
            word = norm(item.get("word", ""))
            reading = norm(item.get("reading", ""))
            rows.append({
                "source_seq": seq,
                "word": word,
                "reading": reading,
                "word_variants": variants(word),
                "kana_only": kana_only(word),
                "level": int(str(item.get("level", f"N{n}")).upper().replace("N","")),
                "meanings_en_seed": [norm(x) for x in item.get("meanings", []) if norm(x)],
                "examples": item.get("examples", []),
            })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows):,} JLPT rows -> {out}")

if __name__ == "__main__":
    main()
