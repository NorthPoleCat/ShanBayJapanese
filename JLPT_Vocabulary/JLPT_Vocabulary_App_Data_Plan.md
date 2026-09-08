# 日语 JLPT 背单词 App：数据源与词库生成计划

> 版本：v0.1  
> 日期：2026-09-08  
> 目标：为 iOS / SwiftUI 日语背单词 App 构建可离线使用、可持续维护、按 JLPT N5～N1 分类的本地词库。

---

## 1. 项目目标

最终构建一套自己的日语词汇数据生产流程：

```text
JLPT N5～N1 词表
        +
JMdict 日语词典
        +
中文释义生成 / 校对
        +
Tatoeba / 自建例句
        ↓
Data Builder
        ↓
vocabulary.sqlite
        ↓
Swift / SwiftUI App
```

核心原则：

1. JLPT 等级与词典释义分离。
2. 原始数据和最终 App 数据分离。
3. 所有外部数据保留来源与许可证信息。
4. 中文释义建立自己的加工层，不直接依赖单一第三方中文词典。
5. SQLite 作为 iOS App 的离线只读基础词库。
6. 用户学习状态与基础词库分离，便于以后升级词库而不影响用户进度。

---

## 2. 第一阶段数据源

### 2.1 OpenJLPT

用途：

- 提供 N5～N1 的 JLPT 词汇等级。
- 提供基础日文词形。
- 提供假名读音。
- 提供英文释义。
- 可利用其已有例句。
- 可作为构建器的第一层 Seed Data。

当前项目数据规模：

| JLPT | 词数 |
| --- | ---: |
| N5 | 662 |
| N4 | 632 |
| N3 | 1,784 |
| N2 | 1,793 |
| N1 | 3,463 |
| 合计 | 8,334 |

注意：

JLPT 官方目前并不公布官方 N5～N1 词汇表，因此这里的等级属于社区整理的考试学习词表，而不能宣传为“JLPT 官方词表”。

项目：

https://github.com/evanclan/OpenJLPT

---

### 2.2 JMdict

用途：

- 日文标准词条。
- 汉字写法。
- 假名读音。
- 词性。
- 多义项。
- 常用词信息。
- 词语标签。
- 使用领域。
- 词形对应关系。

JMdict 将作为词汇信息的主要标准词典来源。

目标不是简单复制 JMdict，而是通过：

```text
OpenJLPT.word
OpenJLPT.reading
        ↓
JMdict Entry Matching
        ↓
JMdict Entry ID
```

建立稳定的词条映射。

项目：

https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project

---

### 2.3 Tatoeba

用途：

- 日语例句。
- 英文翻译。
- 后续可生成中文翻译。
- 为背单词提供上下文。

第一版不需要追求每个单词大量例句。

建议：

```text
每词 1～3 个高质量例句
```

优先级：

```text
短句
自然表达
目标词义明确
难度不要明显高于当前 JLPT Level
```

项目：

https://tatoeba.org/

---

## 3. 中文释义方案

中文释义不直接依赖一个未知授权的网上日中词典。

建议 Pipeline：

```text
JMdict 英文义项
        +
JMdict 词性 / 标签
        +
日文词形
        ↓
LLM 批量生成中文候选释义
        ↓
规则清洗
        ↓
人工抽检 / 修正
        ↓
正式中文词库
```

例如：

原始数据：

```json
{
  "word": "掛ける",
  "reading": "かける",
  "meanings_en": [
    "to hang",
    "to put on",
    "to call",
    "to spend"
  ]
}
```

加工后：

```json
{
  "word": "掛ける",
  "reading": "かける",
  "meanings_zh": [
    "挂；悬挂",
    "戴上；披上",
    "打电话",
    "花费（时间、金钱等）"
  ]
}
```

原则：

- 不要让 LLM 自己决定 JLPT Level。
- 不要让 LLM 自己创造日文读音。
- LLM 主要负责中文表达整理。
- 核心结构化字段仍以可靠词典数据为准。

---

## 4. 最终 SQLite 设计方向

计划产物：

```text
vocabulary.sqlite
```

第一版建议至少包含以下表：

```text
vocabulary
meanings
examples
tags
sources
metadata
```

### vocabulary

负责词本身：

```text
id
jmdict_entry_id
word
reading
jlpt_level
part_of_speech
is_common
frequency_rank
source
```

### meanings

一个词可以有多个义项：

```text
id
vocabulary_id
language
meaning
sense_index
is_primary
```

例如：

```text
食べる
├── zh: 吃
└── en: to eat
```

### examples

```text
id
vocabulary_id
sentence_ja
sentence_zh
sentence_en
source
difficulty
```

### tags

用于以后扩展：

```text
transitive
intransitive
ichidan
godan
noun
adverb
common
formal
colloquial
```

---

## 5. 不建议把用户学习数据放进 vocabulary.sqlite

基础词库：

```text
vocabulary.sqlite
```

只保存公共静态数据。

用户学习状态建议使用：

```text
UserData.sqlite / SwiftData / CoreData
```

例如：

```text
wordID
isFavorite
learnedCount
correctCount
wrongCount
lastReviewDate
nextReviewDate
srsStage
```

通过：

```text
wordID
```

关联基础词库。

这样以后：

```text
vocabulary.sqlite v1
        ↓
vocabulary.sqlite v2
```

可以直接替换，而不会破坏用户的背词进度。

---

## 6. Data Builder 目录结构

下一阶段计划实现：

```text
JLPTVocabularyBuilder/
│
├── README.md
├── requirements.txt
├── Makefile
│
├── config/
│   └── config.json
│
├── data/
│   ├── raw/
│   │   ├── openjlpt/
│   │   ├── jmdict/
│   │   └── tatoeba/
│   │
│   ├── intermediate/
│   │   ├── jlpt_words.json
│   │   ├── matched_words.json
│   │   └── zh_meanings.json
│   │
│   └── output/
│       └── vocabulary.sqlite
│
├── schema/
│   └── vocabulary.sql
│
├── scripts/
│   ├── download_sources.py
│   ├── normalize_jlpt.py
│   ├── parse_jmdict.py
│   ├── match_jmdict.py
│   ├── import_examples.py
│   ├── build_sqlite.py
│   └── validate.py
│
└── go/
    ├── go.mod
    └── cmd/
        └── builder/
            └── main.go
```

---

## 7. Builder 的执行流程

目标是一条命令完成构建：

```bash
make build
```

内部流程：

```text
1. 下载 OpenJLPT
2. 下载 JMdict
3. 下载 / 导入例句
4. 标准化 N5～N1 数据
5. OpenJLPT ↔ JMdict 匹配
6. 输出待生成中文义项
7. 导入中文义项
8. 构建 SQLite
9. 创建索引
10. 校验数据
11. 输出 vocabulary.sqlite
```

最终：

```text
data/output/vocabulary.sqlite
```

---

## 8. JMdict Matching 策略

这是整个 Builder 最重要的一部分之一。

不能只通过：

```text
word == word
```

匹配。

计划按照以下优先级：

### Level 1

```text
word + reading 完全一致
```

最高可信。

### Level 2

```text
word 一致
reading 为空或可推导
```

### Level 3

假名词：

```text
OpenJLPT.word == JMdict.reading
```

### Level 4

存在多个 JMdict Entry：

```text
word
+
reading
+
English Meaning Similarity
```

辅助消歧。

### Level 5

无法自动判断：

```text
manual_review.json
```

进入人工审核队列。

不能为了达到“100%匹配率”而强行匹配错误 Entry。

---

## 9. 数据质量检查

Builder 最后必须运行自动验证：

```text
N5 数量检查
N4 数量检查
N3 数量检查
N2 数量检查
N1 数量检查
```

同时检查：

```text
word 不为空
JLPT level 合法
重复词
重复 word + reading
JMdict 匹配率
中文释义覆盖率
例句覆盖率
孤立 meanings
孤立 examples
```

最终输出类似：

```text
Build Report

JLPT Words:        8,334
JMdict Matched:    8,280
Match Rate:        99.35%

Chinese Meaning:   8,334
Coverage:          100%

Example Coverage:  7,420
Coverage:          89.03%

Manual Review:     54
```

---

## 10. iOS 端计划

最终把：

```text
vocabulary.sqlite
```

直接加入 Xcode Bundle。

例如：

```text
Resources/
└── vocabulary.sqlite
```

Swift Repository：

```text
VocabularyRepository
```

提供：

```swift
func words(level: JLPTLevel) -> [Vocabulary]
func word(id: Int64) -> Vocabulary?
func search(_ keyword: String) -> [Vocabulary]
func randomWords(level: JLPTLevel, count: Int) -> [Vocabulary]
```

后续可以使用：

- SQLite3
- GRDB
- SQLite.swift

第一推荐：

```text
GRDB
```

因为只读数据库查询、FTS5 搜索以及 Codable 映射都比较方便。

---

## 11. 后续可扩展字段

第一版不要一次全部完成，但数据库结构应保留扩展能力。

未来可以增加：

```text
accent
audio
frequency
kanji level
pitch accent
conjugation
synonyms
antonyms
related words
example difficulty
grammar tags
textbook tags
```

还可以增加：

```text
JLPT
标日初级
标日中级
标日高级
大家的日语
Genki
```

等不同词书映射。

这意味着一个词只维护一次：

```text
食べる
```

但可以同时属于：

```text
JLPT N5
标日初级
Genki I
自定义词书
```

所以长期最好把“词本身”和“词书/等级”做成多对多关系。

---

## 12. 推荐的长期数据库模型

比单纯：

```text
vocabulary.jlpt_level
```

更好的长期方案是：

```text
vocabulary
    ↑
word_list_items
    ↓
word_lists
```

例如：

```text
word_lists

1  JLPT N5
2  JLPT N4
3  JLPT N3
4  JLPT N2
5  JLPT N1
6  标准日本语初级上
```

一个单词：

```text
食べる
```

可以加入多个 List。

这样以后这个词库不只是 JLPT App 的词库，而可以成为整个日语学习产品的数据底座。

---

## 13. License / Attribution

构建过程中必须保存：

```text
source_name
source_url
license
source_version
retrieved_at
```

至少需要关注：

### OpenJLPT

当前项目声明 Dataset & Code：

```text
CC BY-SA 4.0
```

### JMdict

需要遵守 EDRDG / JMdict 当前发布条款和署名要求。

### Tatoeba

下载数据存在 Creative Commons 授权要求；具体例句和音频尤其需要分别确认来源许可证。

App 内建议预留：

```text
设置
  └── 关于
       └── 数据来源与许可证
```

不要等 App 上架前才处理 Attribution。

---

## 14. MVP 范围

第一版 Builder 不追求一次做到所有高级功能。

### 必须

- N5～N1。
- 词形。
- 假名。
- JLPT Level。
- 中文释义。
- 英文释义。
- 词性。
- SQLite。
- 数据来源记录。
- 自动 Validation。

### 建议有

- 1～3 条例句。
- JMdict Entry ID。
- Common 标记。
- 基础搜索索引。

### 暂时不要做

- 真人发音。
- Pitch Accent。
- AI 动态生成例句。
- 复杂词频融合。
- 多套教材映射。
- SRS 算法。

这些属于 App 层或第二阶段数据增强。

---

## 15. 下一阶段实际交付物

下一步将实际制作：

```text
JLPTVocabularyBuilder/
```

并包含：

1. `README.md`
2. `schema/vocabulary.sql`
3. Python 数据处理脚本
4. Go Builder / CLI 示例
5. OpenJLPT 导入
6. JMdict XML 解析
7. Entry Matching
8. 中文释义中间格式
9. SQLite Builder
10. Validation
11. Swift / SwiftUI 查询示例
12. 最终 `vocabulary.sqlite`

目标：

```bash
git clone ...
cd JLPTVocabularyBuilder
make build
```

完成后直接得到：

```text
data/output/vocabulary.sqlite
```

---

## 16. 第一阶段结论

当前推荐技术路线：

```text
OpenJLPT
   ↓
确定 N5～N1 学习范围
   ↓
JMdict
   ↓
补充标准词条 / 读音 / 词性 / 英文义项
   ↓
中文释义生成 + 人工校验
   ↓
Tatoeba / 自建例句
   ↓
SQLite Builder
   ↓
vocabulary.sqlite
   ↓
SwiftUI
```

这套架构的核心不是“找到一个现成 JSON 然后塞进 App”，而是建立一个以后可以持续更新的数据生产管线。

一旦 Builder 做好，未来即使：

- OpenJLPT 更新；
- JMdict 更新；
- 修正中文释义；
- 增加例句；
- 增加新的词书；
- 增加 Android / Web 客户端；

都可以重新运行 Builder 生成统一的数据资产，而不需要人工重新整理整个词库。
