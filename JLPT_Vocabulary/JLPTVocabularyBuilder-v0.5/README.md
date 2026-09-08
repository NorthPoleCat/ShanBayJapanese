# JLPTVocabularyBuilder v0.5

v0.5 只新增四项学习数据能力：

1. 词性中文名
2. 常用度
3. 例句与具体 Sense 绑定
4. 干扰项生成依据

不加入动词活用、形容词活用等额外功能。

## Pipeline

```text
OpenJLPT
  ↓
JMdict
  ↓
match_jmdict.py
  ↓
refine_lexicon.py
  ↓
zh_senses.csv
  ↓ 中文 Sense 翻译 / 审核
enrich_learning_data.py
  ↓
build_sqlite.py
  ↓
vocabulary.sqlite
```

完整构建后半段：

```bash
make refine
make sense-template

# 翻译 zh_senses.csv

make audit-senses
make enrich
make db
make validate
```

离线样例：

```bash
make sample
```

## 1. 词性中文名

`vocabulary.pos_zh` / `senses.pos_zh`

例如：

```text
noun        → 名词
verb        → 动词
adjective   → 形容词
adverb      → 副词
particle    → 助词
conjunction → 接续词

Ichidan verb       → 一段动词
Godan verb         → 五段动词
transitive verb    → 他动词
intransitive verb  → 自动词
na-adjective       → な形容词
i-adjective        → い形容词
```

## 2. 常用度

新增：

```text
is_common
common_score
common_rank
```

`common_score` 是 Builder 根据 JMdict priority tag 生成的内部 0～100 分。
它适合 App 内排序、筛选和干扰项匹配。

注意：这个分数不是语料库中的绝对词频。

## 3. 例句 ↔ Sense

`examples` 新增：

```text
sense_id
sense_match_method
sense_match_score
```

自动绑定时，当前版本使用 OpenJLPT 英文例句与 JMdict 英文 gloss 的词汇重叠做保守匹配。

只有达到阈值才绑定；不确定的例句保留 `sense_id = NULL`，避免强行绑定错误义项。

## 4. 干扰项生成依据

新增：

```text
distractor_features
```

字段包含：

```text
same_level
pos_group
pos_zh
reading_length
mora_bucket
script_type
has_kanji
first_char
last_char
meaning_keywords
sense_count
common_score
```

推荐选择题生成策略：

```text
候选池：
同 JLPT Level
    ↓
优先相同词性
    ↓
常用度接近
    ↓
读音长度 / 文字类型接近
    ↓
排除同义词或意义高度重叠词
    ↓
随机选 3 个
```

这些字段只提供“生成依据”，最终干扰项可以在 App 运行时生成，也可以以后离线预生成。
