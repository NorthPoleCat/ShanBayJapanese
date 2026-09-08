#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]


def pick(usage: dict, *keys: str) -> int:
    for k in keys:
        v = usage.get(k)
        if isinstance(v, (int, float)):
            return int(v)
    return 0


def cost(tokens: int, price: float) -> float:
    return tokens / 1_000_000.0 * price


def main():
    p = argparse.ArgumentParser(description='Summarize actual token usage recorded by translate_zh.py.')
    p.add_argument('--input', default=str(ROOT/'data/intermediate/zh_usage.jsonl'))
    p.add_argument('--input-price-per-million', type=float, default=0.0)
    p.add_argument('--output-price-per-million', type=float, default=0.0)
    p.add_argument('--cached-input-price-per-million', type=float, default=None)
    p.add_argument('--currency', default='USD')
    p.add_argument('--report-json', default='')
    args = p.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f'Usage log not found: {path}')

    requests = 0
    prompt = completion = total = cached = 0
    providers, models = set(), set()
    malformed = 0

    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                malformed += 1
                continue
            usage = row.get('usage') or {}
            requests += 1
            providers.add(str(row.get('provider','')))
            models.add(str(row.get('model','')))

            p_tokens = pick(usage, 'prompt_tokens', 'input_tokens')
            c_tokens = pick(usage, 'completion_tokens', 'output_tokens')
            t_tokens = pick(usage, 'total_tokens') or (p_tokens + c_tokens)

            # OpenAI-style nested cached token details when present.
            details = usage.get('prompt_tokens_details') or usage.get('input_tokens_details') or {}
            cached_tokens = pick(details, 'cached_tokens')

            prompt += p_tokens
            completion += c_tokens
            total += t_tokens
            cached += cached_tokens

    uncached_prompt = max(0, prompt - cached)
    cached_price = args.cached_input_price_per_million
    if cached_price is None:
        cached_price = args.input_price_per_million

    input_cost = cost(uncached_prompt, args.input_price_per_million) + cost(cached, cached_price)
    output_cost = cost(completion, args.output_price_per_million)
    total_cost = input_cost + output_cost

    report = {
        'usage_file': str(path),
        'requests': requests,
        'providers': sorted(x for x in providers if x),
        'models': sorted(x for x in models if x),
        'malformed_lines': malformed,
        'tokens': {
            'input': prompt,
            'cached_input': cached,
            'uncached_input': uncached_prompt,
            'output': completion,
            'total': total,
        },
        'pricing': {
            'currency': args.currency,
            'input_per_million': args.input_price_per_million,
            'cached_input_per_million': cached_price,
            'output_per_million': args.output_price_per_million,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
        }
    }

    print('Actual translation usage')
    print('------------------------')
    print(f'Requests:               {requests:,}')
    print(f'Input tokens:           {prompt:,}')
    print(f'  cached input:         {cached:,}')
    print(f'  uncached input:       {uncached_prompt:,}')
    print(f'Output tokens:          {completion:,}')
    print(f'Total tokens:           {total:,}')
    if args.input_price_per_million or args.output_price_per_million:
        print(f'Input cost:             {args.currency} {input_cost:.6f}')
        print(f'Output cost:            {args.currency} {output_cost:.6f}')
        print(f'Actual total cost:      {args.currency} {total_cost:.6f}')
    else:
        print('Cost:                   not calculated (provide pricing arguments)')
    if malformed:
        print(f'Malformed log lines:    {malformed}')

    if args.report_json:
        out = Path(args.report_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'JSON report:            {out}')

if __name__ == '__main__':
    main()
