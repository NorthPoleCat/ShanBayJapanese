#!/usr/bin/env python3
from pathlib import Path
import argparse,json,re
ROOT=Path(__file__).resolve().parents[1]
def classify(pos):
    tags=[x.strip().lower() for x in pos]
    t=' | '.join(tags)
    vc='godan' if any('godan verb' in x for x in tags) else 'ichidan' if any('ichidan verb' in x for x in tags) else 'irregular' if any(('suru verb' in x or 'kuru verb' in x or 'irregular verb' in x) for x in tags) else None
    has_trans=any(x == 'transitive verb' for x in tags)
    has_intrans=any(x == 'intransitive verb' for x in tags)
    tr='both' if (has_trans and has_intrans) else 'transitive' if has_trans else 'intransitive' if has_intrans else 'unknown'
    ac='i' if ('i-adjective' in t or 'adjective (keiyoushi)' in t) else 'na' if ('na-adjective' in t or 'adjectival nouns or quasi-adjectives' in t) else 'no' if 'no-adjective' in t else None
    pg='verb' if 'verb' in t else 'adjective' if ('adjective' in t or 'adjectival' in t) else 'adverb' if 'adverb' in t else 'particle' if 'particle' in t else 'conjunction' if 'conjunction' in t else 'interjection' if 'interjection' in t else 'counter' if 'counter' in t else 'pronoun' if 'pronoun' in t else 'noun' if 'noun' in t else 'other'
    return dict(primary_pos=pos[0] if pos else None,pos_group=pg,verb_class=vc,transitivity=tr,adjective_class=ac)
def reading_for(r):
    if (r.get('reading') or '').strip(): return r['reading'].strip(),'openjlpt'
    if r.get('readings'): return r['readings'][0],'jmdict'
    word=r.get('word','')
    if re.fullmatch(r'[\u3040-\u30ffー・]+',word): return word,'surface'
    return '','missing'
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',default=str(ROOT/'data/intermediate/matched_words.json')); p.add_argument('--output',default=str(ROOT/'data/intermediate/refined_words.json')); a=p.parse_args()
    rows=json.loads(Path(a.input).read_text(encoding='utf-8')); out=[]
    for r in rows:
        q=dict(r); q['reading'],q['reading_source']=reading_for(q); q.update(classify(q.get('pos') or [])); senses=q.get('senses_en') or [q.get('meanings_en_seed') or []]; q['senses']=[dict(sense_index=i,meaning_en='; '.join(gs),meaning_zh='',pos_text=' | '.join(q.get('pos') or []),review_status='pending') for i,gs in enumerate(senses)]; out.append(q)
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); print(f'Refined: {len(out):,}'); print(f'Missing reading after refinement: {sum(not x.get("reading") for x in out):,}')
if __name__=='__main__': main()
