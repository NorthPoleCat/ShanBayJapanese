#!/usr/bin/env python3
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import argparse, csv, json, os, time

ROOT = Path(__file__).resolve().parents[1]

SYSTEM_PROMPT = """You translate Japanese dictionary senses into concise Simplified Chinese.

Rules:
1. Translate EACH sense independently.
2. Preserve semantic distinctions between senses.
3. Return concise dictionary glosses, not explanatory sentences.
4. Never invent JLPT levels, readings, POS, or meanings.
5. Do not merge separate senses.
6. Chinese should be natural for a vocabulary-learning app.
7. Output JSON only.

Return:
{
  "items": [
    {"source_seq": 1, "sense_index": 0, "meaning_zh": "吃"}
  ]
}
"""

def provider_config(provider, model):
    if provider == "openai":
        return (
            "https://api.openai.com/v1/chat/completions",
            os.environ.get("OPENAI_API_KEY"),
            model
        )
    if provider == "deepseek":
        return (
            "https://api.deepseek.com/chat/completions",
            os.environ.get("DEEPSEEK_API_KEY"),
            model
        )
    raise ValueError(provider)

def call_api(url, key, model, batch):
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":json.dumps({"items":batch}, ensure_ascii=False)}
        ]
    }
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    obj = json.loads(content)
    return obj, data.get("usage")

def load_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def save_csv(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(ROOT/"data/intermediate/zh_senses.csv"))
    p.add_argument("--provider", choices=["openai","deepseek"], required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--limit", type=int)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-retries", type=int, default=4)
    args = p.parse_args()

    rows = load_csv(args.input)
    pending = [r for r in rows if not (r.get("meaning_zh") or "").strip()]
    if args.limit:
        pending = pending[:args.limit]

    if not pending:
        print("No pending senses.")
        return

    url, key, model = provider_config(args.provider, args.model)
    if not args.dry_run and not key:
        raise SystemExit(f"Missing API key for {args.provider}")

    usage_path = ROOT/"data/intermediate/zh_sense_usage.jsonl"
    fail_path = ROOT/"data/intermediate/zh_sense_failed.jsonl"

    index = {(r["source_seq"], r["sense_index"]): r for r in rows}

    for start in range(0, len(pending), args.batch_size):
        chunk = pending[start:start+args.batch_size]
        batch = [{
            "source_seq": int(r["source_seq"]),
            "sense_index": int(r["sense_index"]),
            "word": r["word"],
            "reading": r["reading"],
            "pos": r["pos_text"],
            "meaning_en": r["meaning_en"]
        } for r in chunk]

        print(f"Batch {start//args.batch_size+1}: {len(batch)} senses")
        if args.dry_run:
            print(json.dumps(batch[:2], ensure_ascii=False, indent=2))
            continue

        result = None
        usage = None
        err = None
        for attempt in range(args.max_retries):
            try:
                result, usage = call_api(url, key, model, batch)
                break
            except Exception as e:
                err = repr(e)
                time.sleep(min(2**attempt, 16))

        if result is None:
            with fail_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"batch":batch,"error":err}, ensure_ascii=False)+"\n")
            print("  failed")
            continue

        returned = result.get("items", [])
        valid = 0
        for item in returned:
            key2 = (str(item.get("source_seq")), str(item.get("sense_index")))
            target = index.get(key2)
            zh = (item.get("meaning_zh") or "").strip()
            if target is not None and zh:
                target["meaning_zh"] = zh
                target["review_status"] = "pending"
                target["translation_source"] = f"{args.provider}:{model}"
                valid += 1

        save_csv(args.input, rows)
        if usage:
            with usage_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "provider": args.provider,
                    "model": model,
                    "batch_size": len(batch),
                    "usage": usage
                }, ensure_ascii=False)+"\n")
        print(f"  saved {valid}/{len(batch)}")

if __name__ == "__main__":
    main()
