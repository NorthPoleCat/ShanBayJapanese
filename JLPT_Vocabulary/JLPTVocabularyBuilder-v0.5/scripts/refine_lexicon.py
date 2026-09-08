#!/usr/bin/env python3
from pathlib import Path
import argparse, json, re

ROOT = Path(__file__).resolve().parents[1]

def flatten(xs):
    return [x for group in xs for x in group]

def classify_pos(pos_tags):
    text = " | ".join(pos_tags).lower()

    verb_class = None
    if "godan" in text:
        verb_class = "godan"
    elif "ichidan" in text:
        verb_class = "ichidan"
    elif "kuru verb" in text or "suru verb" in text or "irregular verb" in text:
        verb_class = "irregular"

    transitivity = "unknown"
    has_trans = "transitive verb" in text
    has_intrans = "intransitive verb" in text
    if has_trans and has_intrans:
        transitivity = "both"
    elif has_trans:
        transitivity = "transitive"
    elif has_intrans:
        transitivity = "intransitive"

    adjective_class = None
    if "i-adjective" in text or "adjective (keiyoushi)" in text:
        adjective_class = "i"
    elif "na-adjective" in text or "adjectival nouns or quasi-adjectives" in text:
        adjective_class = "na"
    elif "no-adjective" in text:
        adjective_class = "no"

    if "verb" in text:
        pos_group = "verb"
    elif "adjective" in text or "adjectival" in text:
        pos_group = "adjective"
    elif "adverb" in text:
        pos_group = "adverb"
    elif "particle" in text:
        pos_group = "particle"
    elif "conjunction" in text:
        pos_group = "conjunction"
    elif "interjection" in text:
        pos_group = "interjection"
    elif "counter" in text:
        pos_group = "counter"
    elif "pronoun" in text:
        pos_group = "pronoun"
    elif "noun" in text:
        pos_group = "noun"
    else:
        pos_group = "other"

    return {
        "primary_pos": pos_tags[0] if pos_tags else None,
        "pos_group": pos_group,
        "verb_class": verb_class,
        "transitivity": transitivity,
        "adjective_class": adjective_class,
    }

def choose_reading(row):
    current = (row.get("reading") or "").strip()
    if current:
        return current, "openjlpt"
    readings = row.get("readings") or []
    if readings:
        return readings[0], "jmdict"
    # kana-only fallback
    word = row.get("word","")
    if re.fullmatch(r"[\u3040-\u30ffー・]+", word):
        return word, "surface"
    return "", "missing"

def build_senses(row):
    senses_en = row.get("senses_en") or []
    pos_tags = row.get("pos") or []
    result = []
    if senses_en:
        for i, glosses in enumerate(senses_en):
            result.append({
                "sense_index": i,
                "meaning_en": "; ".join(glosses),
                "meaning_zh": "",
                "pos_text": " | ".join(pos_tags),
                "review_status": "pending"
            })
    else:
        seed = row.get("meanings_en_seed") or []
        result.append({
            "sense_index": 0,
            "meaning_en": "; ".join(seed),
            "meaning_zh": "",
            "pos_text": " | ".join(pos_tags),
            "review_status": "pending"
        })
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(ROOT/"data/intermediate/matched_words.json"))
    p.add_argument("--output", default=str(ROOT/"data/intermediate/refined_words.json"))
    args = p.parse_args()

    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))
    refined = []

    for row in rows:
        reading, reading_source = choose_reading(row)
        cls = classify_pos(row.get("pos") or [])
        out = dict(row)
        out["reading"] = reading
        out["reading_source"] = reading_source
        out.update(cls)
        out["senses"] = build_senses(out)
        refined.append(out)

    Path(args.output).write_text(
        json.dumps(refined, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    missing = sum(1 for r in refined if not r.get("reading"))
    print(f"Refined: {len(refined):,}")
    print(f"Missing reading after refinement: {missing:,}")
    print(f"Output: {args.output}")

if __name__ == "__main__":
    main()
