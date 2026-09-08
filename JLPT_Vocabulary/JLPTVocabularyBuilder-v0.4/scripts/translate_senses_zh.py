#!/usr/bin/env python3
from pathlib import Path
from urllib.request import Request,urlopen
import argparse,csv,json,os,time
ROOT=Path(__file__).resolve().parents[1]
SYSTEM_PROMPT='''Translate Japanese dictionary senses into concise Simplified Chinese. Translate each sense independently; preserve distinctions; do not merge senses; never invent readings, JLPT levels, POS or meanings; return concise dictionary glosses rather than explanatory sentences. Output JSON only as {"items":[{"source_seq":1,"sense_index":0,"meaning_zh":"吃"}]}'''
def cfg(provider,model):
    if provider=='openai': return 'https://api.openai.com/v1/chat/completions',os.getenv('OPENAI_API_KEY'),model
    if provider=='deepseek': return 'https://api.deepseek.com/chat/completions',os.getenv('DEEPSEEK_API_KEY'),model
    raise ValueError(provider)
def call(url,key,model,batch):
    payload={'model':model,'temperature':0.1,'response_format':{'type':'json_object'},'messages':[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':json.dumps({'items':batch},ensure_ascii=False)}]}
    req=Request(url,data=json.dumps(payload).encode(),headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},method='POST')
    with urlopen(req,timeout=120) as r: data=json.loads(r.read().decode())
    return json.loads(data['choices'][0]['message']['content']),data.get('usage')
def load(path):
    with Path(path).open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def save(path,rows):
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f: w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',default=str(ROOT/'data/intermediate/zh_senses.csv')); p.add_argument('--provider',choices=['openai','deepseek'],required=True); p.add_argument('--model',required=True); p.add_argument('--batch-size',type=int,default=20); p.add_argument('--limit',type=int); p.add_argument('--dry-run',action='store_true'); p.add_argument('--max-retries',type=int,default=4); a=p.parse_args()
    rows=load(a.input); pending=[r for r in rows if not (r.get('meaning_zh') or '').strip()]; pending=pending[:a.limit] if a.limit else pending
    if not pending: print('No pending senses.'); return
    url,key,model=cfg(a.provider,a.model)
    if not a.dry_run and not key: raise SystemExit(f'Missing API key for {a.provider}')
    idx={(r['source_seq'],r['sense_index']):r for r in rows}; usagep=ROOT/'data/intermediate/zh_sense_usage.jsonl'; failp=ROOT/'data/intermediate/zh_sense_failed.jsonl'
    for start in range(0,len(pending),a.batch_size):
        chunk=pending[start:start+a.batch_size]; batch=[{'source_seq':int(r['source_seq']),'sense_index':int(r['sense_index']),'word':r['word'],'reading':r['reading'],'pos':r['pos_text'],'meaning_en':r['meaning_en']} for r in chunk]
        print(f'Batch {start//a.batch_size+1}: {len(batch)} senses')
        if a.dry_run: print(json.dumps(batch[:2],ensure_ascii=False,indent=2)); continue
        result=usage=None; err=None
        for attempt in range(a.max_retries):
            try: result,usage=call(url,key,model,batch); break
            except Exception as e: err=repr(e); time.sleep(min(2**attempt,16))
        if result is None:
            with failp.open('a',encoding='utf-8') as f: f.write(json.dumps({'batch':batch,'error':err},ensure_ascii=False)+'\n')
            continue
        valid=0
        for item in result.get('items',[]):
            target=idx.get((str(item.get('source_seq')),str(item.get('sense_index')))); zh=(item.get('meaning_zh') or '').strip()
            if target is not None and zh: target['meaning_zh']=zh; target['review_status']='pending'; target['translation_source']=f'{a.provider}:{model}'; valid+=1
        save(a.input,rows)
        if usage:
            with usagep.open('a',encoding='utf-8') as f: f.write(json.dumps({'provider':a.provider,'model':model,'batch_size':len(batch),'usage':usage},ensure_ascii=False)+'\n')
        print(f'  saved {valid}/{len(batch)}')
if __name__=='__main__': main()
