#!/usr/bin/env python3
from pathlib import Path
from urllib.request import Request, urlopen
import argparse, csv, json, os, time

ROOT=Path(__file__).resolve().parents[1]
SYSTEM_PROMPT="""Translate Japanese example sentences into natural Simplified Chinese for a Japanese-learning app.
Use both Japanese and English as context. Preserve meaning, tense, polarity, names, numbers, and tone.
Return concise translations only, with no notes. Do not omit or add information. Output JSON only.
Return: {"items":[{"example_id":1,"sentence_zh":"请后天来。"}]}"""

def config(provider,model):
    if provider=="openai": return "https://api.openai.com/v1/chat/completions",os.environ.get("OPENAI_API_KEY"),model
    return "https://api.deepseek.com/chat/completions",os.environ.get("DEEPSEEK_API_KEY"),model

def call(url,key,model,batch):
    payload={"model":model,"temperature":0.1,"response_format":{"type":"json_object"},"messages":[
        {"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":json.dumps({"items":batch},ensure_ascii=False)}]}
    req=Request(url,data=json.dumps(payload).encode(),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},method="POST")
    with urlopen(req,timeout=120) as resp: data=json.loads(resp.read().decode())
    return json.loads(data["choices"][0]["message"]["content"]),data.get("usage")

def save(path,rows):
    with Path(path).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",default=str(ROOT/"data/intermediate/zh_examples.csv"))
    p.add_argument("--provider",choices=["openai","deepseek"],required=True); p.add_argument("--model",required=True)
    p.add_argument("--batch-size",type=int,default=100); p.add_argument("--limit",type=int); p.add_argument("--max-retries",type=int,default=4)
    args=p.parse_args()
    with Path(args.input).open("r",encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    pending=[r for r in rows if not (r.get("sentence_zh") or "").strip()]
    if args.limit: pending=pending[:args.limit]
    if not pending: print("No pending examples."); return
    url,key,model=config(args.provider,args.model)
    if not key: raise SystemExit(f"Missing API key for {args.provider}")
    by_id={str(r["example_id"]):r for r in rows}
    for start in range(0,len(pending),args.batch_size):
        chunk=pending[start:start+args.batch_size]
        batch=[{"example_id":int(r["example_id"]),"sentence_ja":r["sentence_ja"],"sentence_en":r["sentence_en"]} for r in chunk]
        print(f"Batch {start//args.batch_size+1}: {len(batch)} examples"); result=usage=error=None
        for attempt in range(args.max_retries):
            try: result,usage=call(url,key,model,batch); break
            except Exception as exc: error=repr(exc); time.sleep(min(2**attempt,16))
        if result is None:
            with (ROOT/"data/intermediate/zh_example_failed.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps({"batch":batch,"error":error},ensure_ascii=False)+"\n")
            print("  failed"); continue
        count=0
        for item in result.get("items",[]):
            target=by_id.get(str(item.get("example_id"))); zh=(item.get("sentence_zh") or "").strip()
            if target is not None and zh:
                target["sentence_zh"]=zh; target["review_status"]="pending"; target["translation_source"]=f"{args.provider}:{model}"; count+=1
        save(args.input,rows)
        if usage:
            with (ROOT/"data/intermediate/zh_example_usage.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps({"provider":args.provider,"model":model,"batch_size":len(batch),"usage":usage},ensure_ascii=False)+"\n")
        print(f"  saved {count}/{len(batch)}")

if __name__=="__main__": main()
