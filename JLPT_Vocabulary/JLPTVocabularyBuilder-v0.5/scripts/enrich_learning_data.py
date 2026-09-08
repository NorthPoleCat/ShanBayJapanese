#!/usr/bin/env python3
from pathlib import Path
import argparse, json, math, re

ROOT = Path(__file__).resolve().parents[1]

POS_ZH_MAP = [
    ("verb", "动词"),
    ("adjective", "形容词"),
    ("adverb", "副词"),
    ("noun", "名词"),
    ("pronoun", "代词"),
    ("particle", "助词"),
    ("conjunction", "接续词"),
    ("interjection", "感叹词"),
    ("counter", "量词"),
    ("prefix", "接头词"),
    ("suffix", "接尾词"),
    ("auxiliary", "助动词"),
]

def pos_zh(pos_group, primary_pos="", pos_text=""):
    pg = (pos_group or "").lower()
    full = f"{primary_pos} {pos_text}".lower()

    # More specific labels first.
    if "transitive verb" in full and "intransitive verb" not in full:
        return "他动词"
    if "intransitive verb" in full:
        return "自动词"
    if "ichidan" in full:
        return "一段动词"
    if "godan" in full:
        return "五段动词"
    if "suru verb" in full or "kuru verb" in full or "irregular verb" in full:
        return "不规则动词"
    if "na-adjective" in full or "adjectival nouns or quasi-adjectives" in full:
        return "な形容词"
    if "i-adjective" in full or "adjective (keiyoushi)" in full:
        return "い形容词"

    for key, zh in POS_ZH_MAP:
        if pg == key:
            return zh
    return "其他"

def priority_score(priority_tags):
    # JMdict priority tags roughly encode commonness. We keep a deterministic
    # internal score, not an absolute language-frequency claim.
    score = 0
    for tag in priority_tags or []:
        t = str(tag)
        if t == "news1": score += 40
        elif t == "ichi1": score += 40
        elif t == "spec1": score += 30
        elif t == "gai1": score += 25
        elif t == "news2": score += 20
        elif t == "ichi2": score += 20
        elif t == "spec2": score += 15
        elif t == "gai2": score += 10
        elif t.startswith("nf") and t[2:].isdigit():
            n = int(t[2:])
            score += max(1, 30 - n)
    return min(score, 100)

def script_type(word):
    has_kanji = bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", word or ""))
    has_kana = bool(re.search(r"[\u3040-\u30ffー]", word or ""))
    if has_kanji and has_kana: return "mixed", 1
    if has_kanji: return "kanji", 1
    return "kana", 0

def mora_bucket(reading):
    # Good-enough deterministic bucket for distractor retrieval, not
    # phonological analysis.
    r = re.sub(r"[・\s]", "", reading or "")
    n = len(r)
    if n <= 2: return 2
    if n <= 4: return 4
    if n <= 6: return 6
    return 8

def meaning_keywords(senses):
    text = "；".join((s.get("meaning_zh") or "") for s in senses)
    parts = re.split(r"[；，、,/（）()：:\s]+", text)
    seen = []
    for p in parts:
        p = p.strip()
        if 1 <= len(p) <= 12 and p not in seen:
            seen.append(p)
    return "|".join(seen[:12])

def english_overlap(example_en, meaning_en):
    a = set(re.findall(r"[a-z]+", (example_en or "").lower()))
    b = set(re.findall(r"[a-z]+", (meaning_en or "").lower()))
    stop = {"to","a","an","the","of","on","in","and","or","be","is","are","with","for"}
    a -= stop; b -= stop
    if not a or not b: return 0.0
    return len(a & b) / len(b)

def bind_examples_to_senses(row):
    senses = row.get("senses") or []
    examples = row.get("examples") or []
    for ex in examples:
        best_idx = None
        best_score = 0.0
        for s in senses:
            sc = english_overlap(ex.get("en",""), s.get("meaning_en",""))
            if sc > best_score:
                best_score = sc
                best_idx = s.get("sense_index", 0)

        # Only bind automatically when there is actual lexical evidence.
        if best_idx is not None and best_score >= 0.34:
            ex["sense_index"] = int(best_idx)
            ex["sense_match_method"] = "english_gloss_overlap"
            ex["sense_match_score"] = round(best_score, 4)
        else:
            ex["sense_index"] = None
            ex["sense_match_method"] = "unbound"
            ex["sense_match_score"] = round(best_score, 4)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ROOT/"data/intermediate/refined_words.json"))
    ap.add_argument("--output", default=str(ROOT/"data/intermediate/enriched_words.json"))
    args = ap.parse_args()

    rows = json.loads(Path(args.input).read_text(encoding="utf-8"))

    for r in rows:
        r["pos_zh"] = pos_zh(r.get("pos_group"), r.get("primary_pos",""), " | ".join(r.get("pos") or []))

        # Prefer explicit priority tags from matcher/parser if available.
        priority = r.get("priority_tags") or []
        score = priority_score(priority)
        if score == 0 and r.get("is_common"):
            score = 50
        r["common_score"] = score

        for s in r.get("senses", []):
            s["pos_zh"] = pos_zh(
                s.get("pos_group") or r.get("pos_group"),
                r.get("primary_pos",""),
                s.get("pos_text","")
            )

        bind_examples_to_senses(r)

        st, hk = script_type(r.get("word",""))
        r["distractor_features"] = {
            "same_level": int(r.get("level", 0)),
            "pos_group": r.get("pos_group"),
            "pos_zh": r.get("pos_zh"),
            "reading_length": len(r.get("reading") or ""),
            "mora_bucket": mora_bucket(r.get("reading") or ""),
            "script_type": st,
            "has_kanji": hk,
            "first_char": (r.get("word") or "")[:1],
            "last_char": (r.get("word") or "")[-1:] if r.get("word") else "",
            "meaning_keywords": meaning_keywords(r.get("senses") or []),
            "sense_count": len(r.get("senses") or []),
            "common_score": score,
        }

    # Rank inside the whole vocabulary by score; tied words share stable ordering
    # by source sequence. Rank is useful for "pick similarly common distractors".
    sorted_rows = sorted(rows, key=lambda x: (-int(x.get("common_score",0)), int(x.get("source_seq") or 0)))
    for rank, r in enumerate(sorted_rows, 1):
        r["common_rank"] = rank

    Path(args.output).write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    bound = sum(1 for r in rows for e in r.get("examples",[]) if e.get("sense_index") is not None)
    total_ex = sum(len(r.get("examples",[])) for r in rows)
    print(f"Enriched: {len(rows):,}")
    print(f"Examples bound to sense: {bound:,}/{total_ex:,}")
    print(f"Output: {args.output}")

if __name__ == "__main__":
    main()
