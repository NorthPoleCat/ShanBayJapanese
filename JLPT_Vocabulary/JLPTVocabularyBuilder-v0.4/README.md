# JLPTVocabularyBuilder v0.4

v0.4 的核心升级是 **JMdict Sense ↔ 中文 Sense 一一对应**，并把词性进一步结构化，适合直接作为 Swift / SwiftUI 离线词典数据库。

## Pipeline

```text
OpenJLPT
  ↓ normalize_jlpt.py
JMdict
  ↓ parse_jmdict.py
match_jmdict.py
  ↓ refine_lexicon.py
refined_words.json
  ↓ export_sense_zh_template.py
zh_senses.csv
  ↓ translate_senses_zh.py
  ↓ audit_senses.py
  ↓ build_sqlite.py
vocabulary.sqlite
```

## 新增结构

`vocabulary` 新增：

```text
pos_group
verb_class       godan / ichidan / irregular
transitivity     transitive / intransitive / both / unknown
adjective_class  i / na / no
```

`senses` 每个 JMdict sense 独立保存：

```text
jmdict_sense_index
meaning_en
meaning_zh
pos_text
review_status
translation_source
translation_note
```

例如：

```text
食べる: verb / ichidan / transitive
開く:   verb / godan / intransitive
開ける: verb / ichidan / transitive
静か:   adjective / na
```

## 完整构建

```bash
make download
make normalize
make jmdict
make match
make refine
make sense-template
```

OpenAI：

```bash
export OPENAI_API_KEY="..."
python3 scripts/translate_senses_zh.py --provider openai --model YOUR_MODEL
```

DeepSeek：

```bash
export DEEPSEEK_API_KEY="..."
python3 scripts/translate_senses_zh.py --provider deepseek --model YOUR_MODEL
```

之后：

```bash
make audit-senses
make db
make validate
```

## 读音补全

1. 优先 OpenJLPT reading
2. 缺失时使用 JMdict reading
3. 纯假名词使用 surface 本身
4. 仍缺失则由 validator 报告

## SQLite

主要表：

```text
vocabulary
senses
meanings       # compatibility/simple queries
examples
word_lists
word_list_items
tags
sources
metadata
vocabulary_fts
```

新功能建议优先查询 `senses`，`meanings` 继续保留用于简单查询和兼容。

## Sample

```bash
make sample
```

随包的 `vocabulary.sqlite` 只是结构演示库，不是完整 8,334 词正式库。
