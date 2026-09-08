#!/usr/bin/env python3
from pathlib import Path
import argparse, json, re, sqlite3

ROOT = Path(__file__).resolve().parents[1]

def tokens(text):
    return set(re.findall(r"[a-z]+", (text or "").lower()))

def overlap(seed, gloss):
    a, b = tokens(" ".join(seed)), tokens(gloss)
    return len(a & b) / len(a | b) if a and b else 0.0

def candidate_ids(con, word, reading):
    ids = set()
    if reading:
        for (eid,) in con.execute("""
            SELECT DISTINCT e.ent_seq
            FROM entry e
            LEFT JOIN kanji k ON k.ent_seq=e.ent_seq
            JOIN reading r ON r.ent_seq=e.ent_seq
            WHERE r.reb=? AND (k.keb=? OR r.reb=?)
        """, (reading, word, word)):
            ids.add(eid)
    else:
        for (eid,) in con.execute("""
            SELECT ent_seq FROM kanji WHERE keb=?
            UNION SELECT ent_seq FROM reading WHERE reb=?
        """, (word, word)):
            ids.add(eid)
    return ids

def fetch_entry(con, eid):
    kanji = [x[0] for x in con.execute("SELECT keb FROM kanji WHERE ent_seq=?", (eid,))]
    readings = [x[0] for x in con.execute("SELECT reb FROM reading WHERE ent_seq=?", (eid,))]
    senses, pos = [], []
    for _, p, gloss in con.execute("SELECT sense_index,pos,gloss_en FROM sense WHERE ent_seq=? ORDER BY sense_index", (eid,)):
        senses.append([x for x in (gloss or "").split("|") if x])
        pos.extend([x for x in (p or "").split("|") if x])
    common = bool(con.execute("SELECT is_common FROM entry WHERE ent_seq=?", (eid,)).fetchone()[0])
    return {"jmdict_entry_id":eid,"kanji":kanji,"readings":readings,
            "senses_en":senses,"pos":list(dict.fromkeys(pos)),"is_common":common}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jlpt", default=str(ROOT / "data/intermediate/jlpt_words.json"))
    p.add_argument("--jmdict", default=str(ROOT / "data/intermediate/jmdict_index.sqlite"))
    p.add_argument("--output", default=str(ROOT / "data/intermediate/matched_words.json"))
    p.add_argument("--manual", default=str(ROOT / "data/intermediate/manual_review.json"))
    args = p.parse_args()

    rows = json.loads(Path(args.jlpt).read_text(encoding="utf-8"))
    con = sqlite3.connect(args.jmdict)
    matched, manual = [], []

    for item in rows:
        ids = set()
        for v in item.get("word_variants", [item["word"]]):
            ids |= candidate_ids(con, v, item.get("reading",""))

        scored = []
        for eid in ids:
            e = fetch_entry(con, eid)
            score, method = 0.0, "candidate"
            if item.get("reading") and item["reading"] in e["readings"]:
                score += 0.45; method = "word+reading"
            if any(v in e["kanji"] for v in item.get("word_variants", [])):
                score += 0.40
                if method != "word+reading": method = "word"
            if item["word"] in e["readings"]:
                score += 0.35; method = "kana-reading"
            gloss = " ".join(g for s in e["senses_en"] for g in s)
            score += 0.12 * overlap(item.get("meanings_en_seed", []), gloss)
            if e["is_common"]: score += 0.03
            scored.append((score, e, method))

        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:
            out = dict(item, match_status="unmatched", match_score=0.0)
            matched.append(out); manual.append(out); continue

        best = scored[0]
        second = scored[1][0] if len(scored) > 1 else -1
        ambiguous = len(scored) > 1 and best[0] - second < 0.08
        out = dict(item)
        out.update(best[1])
        out["match_method"] = best[2]
        out["match_score"] = round(best[0], 4)
        out["match_status"] = "ambiguous" if ambiguous else "matched"
        matched.append(out)
        if ambiguous or best[0] < 0.40:
            out2 = dict(out)
            out2["candidate_ids"] = [x[1]["jmdict_entry_id"] for x in scored[:5]]
            manual.append(out2)

    Path(args.output).write_text(json.dumps(matched, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.manual).write_text(json.dumps(manual, ensure_ascii=False, indent=2), encoding="utf-8")
    con.close()
    print(f"Matched output: {len(matched):,}; manual review: {len(manual):,}")

if __name__ == "__main__":
    main()
