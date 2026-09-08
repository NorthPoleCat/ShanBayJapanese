#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse, csv, json, os, time, urllib.request, urllib.error

ROOT = Path(__file__).resolve().parents[1]

SYSTEM_PROMPT = '''你是日语词典编辑。你的任务是把日语词条的英文释义整理成适合中文学习者背单词的简体中文释义。
规则：
1. 不修改日文词形、读音、JLPT等级、JMdict ID。
2. 只依据给定日语词、读音、词性、英文义项生成中文，不要臆造新的核心词义。
3. 输出简洁、自然、适合背单词；避免整句解释。
4. 多义词按常见义项拆分，最多 6 个中文义项。
5. 每个义项尽量 2~12 个汉字；必要时可加括号说明搭配范围。
6. 仅返回合法 JSON，不要 Markdown，不要解释。
返回格式：{"items":[{"source_seq":1,"meaning_zh":["吃"]}]}
'''

class ProviderError(RuntimeError):
    pass

class ChatCompletionsProvider:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 120):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def translate_batch(self, items: list[dict]) -> dict:
        url = self.base_url + '/chat/completions'
        body = {
            'model': self.model,
            'temperature': 0.1,
            'response_format': {'type': 'json_object'},
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': json.dumps({'items': items}, ensure_ascii=False)}
            ]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': 'JLPTVocabularyBuilder/0.2'
            },
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                payload = json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', errors='replace')
            raise ProviderError(f'HTTP {e.code}: {detail[:1000]}') from e
        except Exception as e:
            raise ProviderError(str(e)) from e

        try:
            content = payload['choices'][0]['message']['content']
            return json.loads(content), (payload.get('usage') or {})
        except Exception as e:
            raise ProviderError(f'Invalid provider response: {payload}') from e


def load_rows(csv_path: Path):
    with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_rows(csv_path: Path, rows: list[dict], fieldnames: list[str]):
    tmp = csv_path.with_suffix(csv_path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)
    tmp.replace(csv_path)


def validate_response(response: dict, requested_ids: set[str]) -> dict[str, str]:
    if not isinstance(response, dict) or not isinstance(response.get('items'), list):
        raise ValueError('Response must contain items array')
    out = {}
    for item in response['items']:
        sid = str(item.get('source_seq', ''))
        if sid not in requested_ids:
            continue
        meanings = item.get('meaning_zh')
        if isinstance(meanings, str):
            meanings = [meanings]
        if not isinstance(meanings, list):
            continue
        cleaned = []
        for x in meanings[:6]:
            if isinstance(x, str):
                x = x.strip().replace('|', '；')
                if x:
                    cleaned.append(x)
        if cleaned:
            out[sid] = '；'.join(cleaned)
    return out


def to_prompt_item(row: dict):
    return {
        'source_seq': int(row['source_seq']),
        'word': row.get('word',''),
        'reading': row.get('reading',''),
        'jlpt_level': row.get('jlpt_level',''),
        'jmdict_entry_id': row.get('jmdict_entry_id',''),
        'pos': row.get('pos',''),
        'meaning_en': row.get('meaning_en','')
    }


def main():
    p = argparse.ArgumentParser(description='Batch-generate Simplified Chinese meanings with checkpointing.')
    p.add_argument('--input', default=str(ROOT/'data/intermediate/zh_meanings.csv'))
    p.add_argument('--provider', choices=['openai','deepseek'], default='openai')
    p.add_argument('--model', default=None)
    p.add_argument('--batch-size', type=int, default=20)
    p.add_argument('--max-retries', type=int, default=4)
    p.add_argument('--sleep', type=float, default=1.0)
    p.add_argument('--limit', type=int, default=0, help='0 = no limit')
    p.add_argument('--overwrite', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    csv_path = Path(args.input)
    rows = load_rows(csv_path)
    if not rows:
        raise SystemExit('No rows found')
    fields = list(rows[0].keys())

    if args.provider == 'openai':
        key = os.getenv('OPENAI_API_KEY','')
        base = os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1')
        model = args.model or os.getenv('OPENAI_MODEL','gpt-5-mini')
    else:
        key = os.getenv('DEEPSEEK_API_KEY','')
        base = os.getenv('DEEPSEEK_BASE_URL','https://api.deepseek.com/v1')
        model = args.model or os.getenv('DEEPSEEK_MODEL','deepseek-chat')

    pending = [r for r in rows if args.overwrite or not (r.get('meaning_zh') or '').strip()]
    if args.limit > 0:
        pending = pending[:args.limit]
    print(f'Total rows: {len(rows):,}; pending: {len(pending):,}; provider={args.provider}; model={model}')
    if args.dry_run:
        print(json.dumps([to_prompt_item(r) for r in pending[:args.batch_size]], ensure_ascii=False, indent=2))
        return
    if not key:
        env_name = 'OPENAI_API_KEY' if args.provider == 'openai' else 'DEEPSEEK_API_KEY'
        raise SystemExit(f'Missing {env_name}')

    provider = ChatCompletionsProvider(base, key, model)
    by_id = {str(r['source_seq']): r for r in rows}
    failed_path = ROOT/'data/intermediate/zh_failed.jsonl'
    usage_path = ROOT/'data/intermediate/zh_usage.jsonl'

    done = 0
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start:start+args.batch_size]
        payload = [to_prompt_item(r) for r in batch]
        ids = {str(r['source_seq']) for r in batch}
        err = None
        result = None
        usage = {}
        for attempt in range(1, args.max_retries+1):
            try:
                raw, usage = provider.translate_batch(payload)
                result = validate_response(raw, ids)
                missing = ids - set(result)
                if missing:
                    raise ValueError(f'Missing source_seq(s): {sorted(missing)}')
                break
            except Exception as e:
                err = e
                if attempt < args.max_retries:
                    delay = min(30.0, args.sleep * (2 ** (attempt-1)))
                    print(f'Batch {start//args.batch_size+1}: attempt {attempt} failed: {e}; retry in {delay:.1f}s')
                    time.sleep(delay)

        if result is None:
            with failed_path.open('a', encoding='utf-8') as f:
                f.write(json.dumps({'source_seq': sorted(ids), 'error': str(err), 'payload': payload}, ensure_ascii=False) + '\n')
            print(f'Batch failed permanently: {err}')
            continue

        for sid, zh in result.items():
            by_id[sid]['meaning_zh'] = zh
            done += 1
        write_rows(csv_path, rows, fields)
        if usage:
            with usage_path.open('a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'provider': args.provider,
                    'model': model,
                    'batch_index': start//args.batch_size + 1,
                    'source_seq': sorted(ids),
                    'usage': usage
                }, ensure_ascii=False) + '\n')
        print(f'Checkpoint: translated {done:,}/{len(pending):,}')
        time.sleep(args.sleep)

    print(f'Done. CSV updated in place: {csv_path}')
    if failed_path.exists():
        print(f'Failures, if any: {failed_path}')
    if usage_path.exists():
        print(f'Actual API usage log: {usage_path}')

if __name__ == '__main__':
    main()
