#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import csv
import json
import math
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]

# Keep this aligned with translate_zh.py. Imported when possible so the estimator
# measures the actual system prompt used by the translator.
try:
    from translate_zh import SYSTEM_PROMPT, to_prompt_item
except Exception:
    SYSTEM_PROMPT = """你是日语词典编辑。你的任务是把日语词条的英文释义整理成适合中文学习者背单词的简体中文释义。"""
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


def load_rows(path: Path) -> list[dict]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def heuristic_tokens(text: str) -> int:
    """Conservative planning heuristic for mixed Chinese/Japanese/English text.

    It is intentionally model-independent. CJK characters tend to tokenize more
    densely than English, while JSON punctuation/ASCII adds overhead. The goal is
    budgeting, not reproducing a provider tokenizer exactly.
    """
    if not text:
        return 0
    cjk = 0
    ascii_chars = 0
    other = 0
    for ch in text:
        o = ord(ch)
        if (0x3040 <= o <= 0x30FF) or (0x3400 <= o <= 0x9FFF) or (0xF900 <= o <= 0xFAFF):
            cjk += 1
        elif o < 128:
            ascii_chars += 1
        else:
            other += 1
    # ~1 token/CJK character, ~4 ASCII chars/token, conservative for punctuation.
    return math.ceil(cjk * 1.05 + ascii_chars / 3.8 + other / 2.0)


def make_token_counter(model: str | None) -> tuple[Callable[[str], int], str]:
    """Use tiktoken when already installed; otherwise standard-library heuristic."""
    try:
        import tiktoken  # type: ignore
        try:
            enc = tiktoken.encoding_for_model(model or 'gpt-4o-mini')
        except Exception:
            enc = tiktoken.get_encoding('o200k_base')
        return lambda s: len(enc.encode(s)), f'tiktoken:{enc.name}'
    except Exception:
        return heuristic_tokens, 'heuristic-mixed-cjk-v1'


def expected_output_text(batch: list[dict], avg_senses: float, avg_chars_per_sense: float) -> str:
    # Model output shape: {"items":[{"source_seq":1,"meaning_zh":["吃"]}, ...]}
    # Build a synthetic response with the configured average size so JSON overhead
    # is included in the token estimate.
    items = []
    full = int(avg_senses)
    extra = avg_senses - full
    for i, row in enumerate(batch):
        senses = max(1, full + (1 if (i / max(1, len(batch))) < extra else 0))
        # Use CJK chars because output is Simplified Chinese.
        one = '释' * max(1, int(round(avg_chars_per_sense)))
        items.append({'source_seq': int(row['source_seq']), 'meaning_zh': [one] * senses})
    return json.dumps({'items': items}, ensure_ascii=False, separators=(',', ':'))


def batch_input_text(batch: list[dict]) -> str:
    payload = {'items': [to_prompt_item(r) for r in batch]}
    # Approximate messages content plus small Chat Completions role/framing overhead.
    return SYSTEM_PROMPT + '\n' + json.dumps(payload, ensure_ascii=False, separators=(',', ':'))


def money(tokens: int, price_per_million: float) -> float:
    return tokens / 1_000_000.0 * price_per_million


def main():
    p = argparse.ArgumentParser(
        description='Estimate requests, tokens and optional translation cost before running translate_zh.py.'
    )
    p.add_argument('--input', default=str(ROOT/'data/intermediate/zh_meanings.csv'))
    p.add_argument('--batch-size', type=int, default=20)
    p.add_argument('--limit', type=int, default=0, help='0 = all pending rows')
    p.add_argument('--overwrite', action='store_true', help='Estimate all rows, including already translated rows')
    p.add_argument('--model', default='', help='Used only for tokenizer selection/report labeling')
    p.add_argument('--provider', default='', help='Report label only, e.g. openai/deepseek')
    p.add_argument('--avg-senses', type=float, default=2.2,
                   help='Expected average number of Chinese senses per word')
    p.add_argument('--avg-chars-per-sense', type=float, default=5.5,
                   help='Expected average Chinese characters per sense')
    p.add_argument('--input-price-per-million', type=float, default=0.0,
                   help='Currency units per 1M input tokens; 0 disables cost estimate')
    p.add_argument('--output-price-per-million', type=float, default=0.0,
                   help='Currency units per 1M output tokens; 0 disables cost estimate')
    p.add_argument('--currency', default='USD')
    p.add_argument('--retry-rate', type=float, default=0.03,
                   help='Planning retry overhead, e.g. 0.03 = +3%%')
    p.add_argument('--report-json', default='', help='Optional JSON report output path')
    p.add_argument('--batch-report-csv', default='', help='Optional per-batch CSV report path')
    args = p.parse_args()

    if args.batch_size <= 0:
        raise SystemExit('--batch-size must be > 0')
    if args.avg_senses <= 0 or args.avg_chars_per_sense <= 0:
        raise SystemExit('--avg-senses and --avg-chars-per-sense must be > 0')
    if args.retry_rate < 0:
        raise SystemExit('--retry-rate must be >= 0')

    rows = load_rows(Path(args.input))
    pending = rows if args.overwrite else [r for r in rows if not (r.get('meaning_zh') or '').strip()]
    if args.limit > 0:
        pending = pending[:args.limit]

    counter, tokenizer_name = make_token_counter(args.model or None)
    batches = [pending[i:i+args.batch_size] for i in range(0, len(pending), args.batch_size)]

    batch_stats = []
    for idx, batch in enumerate(batches, start=1):
        input_text = batch_input_text(batch)
        output_text = expected_output_text(batch, args.avg_senses, args.avg_chars_per_sense)
        input_tokens = counter(input_text)
        output_tokens = counter(output_text)
        batch_stats.append({
            'batch': idx,
            'words': len(batch),
            'first_source_seq': batch[0].get('source_seq','') if batch else '',
            'last_source_seq': batch[-1].get('source_seq','') if batch else '',
            'input_chars': len(input_text),
            'output_chars_est': len(output_text),
            'input_tokens_est': input_tokens,
            'output_tokens_est': output_tokens,
        })

    raw_input = sum(x['input_tokens_est'] for x in batch_stats)
    raw_output = sum(x['output_tokens_est'] for x in batch_stats)
    retry_multiplier = 1.0 + args.retry_rate
    planned_input = math.ceil(raw_input * retry_multiplier)
    planned_output = math.ceil(raw_output * retry_multiplier)

    input_cost = money(planned_input, args.input_price_per_million)
    output_cost = money(planned_output, args.output_price_per_million)
    total_cost = input_cost + output_cost

    completed = sum(1 for r in rows if (r.get('meaning_zh') or '').strip())
    report = {
        'input_file': str(Path(args.input)),
        'provider': args.provider,
        'model': args.model,
        'tokenizer': tokenizer_name,
        'total_rows': len(rows),
        'already_translated': completed,
        'pending_selected': len(pending),
        'batch_size': args.batch_size,
        'requests': len(batches),
        'avg_senses': args.avg_senses,
        'avg_chars_per_sense': args.avg_chars_per_sense,
        'retry_rate': args.retry_rate,
        'tokens': {
            'input_raw_est': raw_input,
            'output_raw_est': raw_output,
            'input_with_retry_est': planned_input,
            'output_with_retry_est': planned_output,
            'total_with_retry_est': planned_input + planned_output,
        },
        'pricing': {
            'currency': args.currency,
            'input_per_million': args.input_price_per_million,
            'output_per_million': args.output_price_per_million,
            'input_cost_est': round(input_cost, 6),
            'output_cost_est': round(output_cost, 6),
            'total_cost_est': round(total_cost, 6),
        },
    }

    print('Translation estimate')
    print('--------------------')
    print(f"Rows in CSV:          {len(rows):,}")
    print(f"Already translated:   {completed:,}")
    print(f"Rows to process:       {len(pending):,}")
    print(f"Batch size:            {args.batch_size:,}")
    print(f"Estimated requests:    {len(batches):,}")
    print(f"Tokenizer:             {tokenizer_name}")
    print(f"Input tokens (raw):    {raw_input:,}")
    print(f"Output tokens (raw):   {raw_output:,}")
    print(f"Retry reserve:         {args.retry_rate*100:.1f}%")
    print(f"Input tokens (plan):   {planned_input:,}")
    print(f"Output tokens (plan):  {planned_output:,}")
    print(f"Total tokens (plan):   {planned_input+planned_output:,}")

    if args.input_price_per_million or args.output_price_per_million:
        print(f"Input cost:            {args.currency} {input_cost:.6f}")
        print(f"Output cost:           {args.currency} {output_cost:.6f}")
        print(f"Estimated total cost:  {args.currency} {total_cost:.6f}")
    else:
        print('Cost:                  not calculated (provide --input-price-per-million and --output-price-per-million)')

    if args.report_json:
        out = Path(args.report_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'JSON report:           {out}')

    if args.batch_report_csv:
        out = Path(args.batch_report_csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('w', encoding='utf-8-sig', newline='') as f:
            fields = list(batch_stats[0].keys()) if batch_stats else [
                'batch','words','first_source_seq','last_source_seq','input_chars',
                'output_chars_est','input_tokens_est','output_tokens_est'
            ]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader(); w.writerows(batch_stats)
        print(f'Batch CSV report:      {out}')

if __name__ == '__main__':
    main()
