# JLPT Vocabulary v0.5 SQLite 数据字典

本文档说明 `JLPTVocabularyBuilder-v0.5` 最终导出的 `vocabulary.sqlite`。当前 schema 版本为 `3`，Builder 版本为 `0.5.0`。

## 数据来源与处理链

```text
OpenJLPT N5～N1 词表
  → 规范化词形、读音、等级、英文种子释义和例句
JMdict
  → 解析词条、写法、读音、词性、英文义项和 priority 标签
两者匹配
  → 细化词性和义项
  → 中文义项翻译/审核（可选，但发布前建议完成）
  → 补充常用度、例句义项绑定、干扰项特征
  → SQLite + FTS5 全文检索表
```

JLPT 等级来自社区项目 OpenJLPT，不是官方公布的固定词表。JMdict 是词典信息的主要来源。当前构建器只把 OpenJLPT 作为 `vocabulary.source_id`，JMdict 的来源记录保存在 `sources`，两者的关联由 `jmdict_entry_id` 表示。

## 表之间的关系

```text
sources 1 ── N vocabulary 1 ── N senses
                         ├── N meanings
                         ├── N examples ── 0..1 senses
                         ├── 1 distractor_features
                         ├── N tags（经 vocabulary_tags）
                         └── N word_lists（经 word_list_items）

vocabulary_fts：vocabulary 与 senses 释义的检索投影
metadata：数据库版本、构建时间和统计信息
```

## `sources`：数据来源

| 字段 | 含义 |
| --- | --- |
| `id` | 来源内部主键。 |
| `name` | 唯一来源名称，如 `OpenJLPT`、`JMdict`。 |
| `url` | 来源主页或项目地址。 |
| `license` | 许可证或发布前核验提示。 |
| `retrieved_at` | UTC ISO 8601 格式的构建/获取时间。 |

## `vocabulary`：词条主表

一行表示一个 OpenJLPT 词条。同一词形和读音如果出现在不同 JLPT 等级，可以各有一行；唯一约束是 `(word, reading, jlpt_level)`。

| 字段 | 含义 |
| --- | --- |
| `id` | App 内使用的词条主键。 |
| `jmdict_entry_id` | 匹配到的 JMdict `ent_seq`；未匹配时为 `NULL`。它是关联词典原词条的稳定标识，不是本库主键。 |
| `word` | 主要展示词形，可能是汉字、假名或混合书写。 |
| `reading` | 假名读音；优先使用 OpenJLPT，缺失时尝试 JMdict 或纯假名词形。 |
| `jlpt_level` | 1～5，分别表示 N1～N5。数字越小等级越高。 |
| `primary_pos` | JMdict 返回的第一个原始英文词性标签。它便于追溯，但不能代表所有义项。 |
| `pos_group` | Builder 归一化的大类：`verb`、`adjective`、`adverb`、`noun`、`pronoun`、`particle`、`conjunction`、`interjection`、`counter` 或 `other`。 |
| `pos_zh` | 面向中文界面的词性名称，如“名词”“五段动词”“な形容词”。具体标签优先于大类。 |
| `verb_class` | 动词活用大类：`godan`、`ichidan`、`irregular`；非动词或无法判断时为 `NULL`。本版本不生成活用形。 |
| `transitivity` | `transitive`（他动）、`intransitive`（自动）、`both` 或 `unknown`。 |
| `adjective_class` | `i`、`na`、`no`；非形容词或无法判断时为 `NULL`。 |
| `is_common` | 0/1。JMdict 是否给该词条附带任意 priority 标签。 |
| `common_score` | Builder 根据 `news`、`ichi`、`spec`、`gai`、`nf` 等 JMdict priority 标签累计并截断到 0～100 的内部常用度分数。适合排序和候选匹配，不是语料词频。 |
| `common_rank` | 全库按 `common_score` 降序、`source_seq` 稳定排序得到的名次；同分也会占不同名次。 |
| `match_method` | OpenJLPT 到 JMdict 的主要匹配依据，如 `word+reading`、`word`、`kana-reading`。 |
| `match_score` | 启发式匹配置信分，由读音、词形、英文释义重叠和常用标记加权产生；不是概率。 |
| `source_id` | 指向 `sources`，表示词表条目的直接来源。 |

## `senses`：按 JMdict 划分的义项

一行表示某个词的一个独立义项，`(vocabulary_id, jmdict_sense_index)` 唯一。

| 字段 | 含义 |
| --- | --- |
| `id` | 义项主键，供例句绑定。 |
| `vocabulary_id` | 所属词条；删除词条时级联删除。 |
| `jmdict_sense_index` | JMdict 词条中的义项序号，从 0 开始。未匹配词使用 OpenJLPT 英文种子释义生成第 0 项。 |
| `meaning_en` | 该义项的英文 gloss；同一 JMdict sense 内多个 gloss 用分号拼接。 |
| `meaning_zh` | 简体中文释义。它来自独立翻译/审核 CSV；未翻译时为 `NULL`。 |
| `pos_text` | 该词条解析出的原始 JMdict 英文词性标签，用 ` | ` 连接。当前实现按词条汇总，未完整保留每个 sense 自己的限制信息。 |
| `pos_group` / `pos_zh` | 义项层的归一化词性大类和中文标签。 |
| `is_primary` | 0/1；当前仅 `jmdict_sense_index = 0` 被视为主要义项。 |
| `review_status` | 中文翻译审核状态，默认 `pending`。 |
| `translation_source` | 中文释义来源，如模型提供商和模型名。 |
| `translation_note` | 翻译或人工审核备注。 |

## `meanings`：便于按语言读取的扁平释义

它是 `senses` 中英文/中文释义的冗余读取层，不是另一套独立义项。

| 字段 | 含义 |
| --- | --- |
| `id` | 释义行主键。 |
| `vocabulary_id` | 所属词条。 |
| `language` | `en` 或 `zh-Hans`。 |
| `meaning` | 对应语言的释义文本。 |
| `sense_index` | 对应 `jmdict_sense_index`。 |
| `is_primary` | 是否是第 0 个义项。 |

## `examples`：例句

每个词最多写入 OpenJLPT 的前三条例句。

| 字段 | 含义 |
| --- | --- |
| `id` | 例句主键。 |
| `vocabulary_id` | 例句所属目标词。 |
| `sense_id` | 自动判断出的具体义项；证据不足时为 `NULL`，删除义项后也会置空。 |
| `sentence_ja` / `sentence_en` / `sentence_zh` | 日文、英文和中文句子。中文由 DeepSeek 根据日文原句与英文译文共同生成；重复例句只翻译一次，再回填所有记录。 |
| `source` | 例句来源，当前为 `OpenJLPT`。 |
| `source_external_id` | 来源侧 ID；当前构建流程尚未写入。 |
| `difficulty` | 预留的例句难度；当前构建流程尚未写入。 |
| `sense_match_method` | 当前为 `english_gloss_overlap` 或 `unbound`。 |
| `sense_match_score` | 英文例句单词集合与英文义项单词集合的重叠分数；达到 0.34 才绑定。它是启发式分数，不是语义模型置信度。 |

## `distractor_features`：选择题干扰项特征

每个词条恰好一行，用于运行时筛选“形式相近但答案不同”的候选项，不是预生成的错误答案。

| 字段 | 含义 |
| --- | --- |
| `vocabulary_id` | 同时是主键和外键。 |
| `same_level` | 实际保存该词的 JLPT 数字等级；名称表达“按同等级筛选”的用途。 |
| `pos_group` / `pos_zh` | 用于优先匹配相同词性。 |
| `reading_length` | 读音字符串的 Unicode 字符数。 |
| `mora_bucket` | 读音长度的粗分桶：不超过 2、4、6 分别为 2、4、6，更长为 8；它不是严格的日语音拍分析。 |
| `script_type` | `kanji`（仅检测到汉字）、`kana`（未检测到汉字）或 `mixed`（汉字和假名都有）。 |
| `has_kanji` | 0/1，词形是否包含 CJK 汉字。 |
| `first_char` / `last_char` | 词形首尾字符。 |
| `meaning_keywords` | 从中文义项按标点切出的最多 12 个关键词，以 `|` 连接；中文未翻译时为空。 |
| `sense_count` | 义项数量。 |
| `common_score` | 从主表复制的常用度，方便候选检索。 |

## 标签与词表

- `tags(id, name)`：可复用标签字典；当前构建流程只建表，尚未导入标签。
- `vocabulary_tags(vocabulary_id, tag_id)`：词条与标签的多对多关联。
- `word_lists(id, code, name, source)`：逻辑词表，当前有 `JLPT_N1`～`JLPT_N5`。
- `word_list_items(word_list_id, vocabulary_id, sort_order)`：词表成员及 OpenJLPT 原始顺序。

## `metadata`：构建元数据

键值表，当前写入：

- `schema_version`：数据库结构版本。
- `builder_version`：生成器版本。
- `built_at`：UTC ISO 8601 构建时间。
- `word_count`：词条数。
- `sense_count`：义项数。
- `example_zh_count`：已有中文翻译的例句记录数。
- `example_bound_count`：成功绑定具体义项的例句数。

## `vocabulary_fts`：FTS5 搜索索引

字段为 `vocabulary_id`、`word`、`reading`、`meaning_zh`、`meaning_en`。每个词条一行，释义由它的全部 sense 拼接。`vocabulary_id` 为 `UNINDEXED`，其余字段用 `unicode61` 分词。

注意：`unicode61` 对英文单词搜索很有效，但对日语/中文的逐字前缀搜索能力有限；App 若要支持任意日文片段，宜用主表 `LIKE`，或以后改用适合 CJK 的 n-gram 索引。

## 当前全量构建结果（2026-09-08）

| 项目 | 数量 |
| --- | ---: |
| 词条 | 8,334 |
| N1 / N2 / N3 / N4 / N5 | 3,463 / 1,793 / 1,784 / 632 / 662 |
| JMdict 已匹配 / 未匹配 | 8,199 / 135 |
| 义项 | 17,750 |
| 例句 | 14,362 |
| 中文例句 | 14,362 / 14,362（12,196 条唯一例句经 DeepSeek `deepseek-chat` 生成） |
| 已绑定具体义项的例句 | 3,214 |
| 中文义项 | 17,750 / 17,750（DeepSeek `deepseek-chat` 生成，待人工抽检） |

## 使用时的重要约束

1. 基础词库应作为 App Bundle 内的只读数据库；收藏、学习进度和复习记录应放在单独的用户数据库。
2. `common_score`、`match_score`、`sense_match_score` 都是 Builder 的启发式内部指标，不能对外描述为官方频率或准确概率。
3. 135 个未匹配词以及 `manual_review.json` 中的歧义/低分项应在正式发布前人工复核。
4. 中文释义完成自动翻译后仍应抽检，并用 `review_status` 标记审核结果。
5. 发布前应再次核验 OpenJLPT 与 JMdict 的最新许可和署名要求。
