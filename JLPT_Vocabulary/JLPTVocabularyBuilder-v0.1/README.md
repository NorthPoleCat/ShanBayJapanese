# JLPTVocabularyBuilder

目标：把 JLPT N5～N1 社区词表与 JMdict 对齐，经过中文释义加工后生成可直接放入 Swift / SwiftUI App 的 `vocabulary.sqlite`。

## 数据流程

```text
OpenJLPT
  ↓ normalize_jlpt.py
JMdict_e.gz
  ↓ parse_jmdict.py
match_jmdict.py
  ↓
matched_words.json
  ↓
zh_meanings.csv（LLM/人工校对）
  ↓
build_sqlite.py
  ↓
vocabulary.sqlite
```

## 先验证项目

无需联网：

```bash
make sample
```

会生成：

```text
data/output/vocabulary.sqlite
```

注意：随包的 `vocabulary.sqlite` 是 15 词的结构与代码演示库，不是完整 JLPT 词库。

## 构建完整词库

```bash
make download
make normalize
make jmdict
make match
make zh-template
```

然后编辑：

```text
data/intermediate/zh_meanings.csv
```

填写 `meaning_zh`，多个义项使用中文分号：

```text
挂；悬挂；打电话；花费
```

最后：

```bash
make db
make validate
```

完整构建的参考 JLPT 词条数来自当前 OpenJLPT：

- N5: 662
- N4: 632
- N3: 1,784
- N2: 1,793
- N1: 3,463
- Total: 8,334

## 为什么中文释义不写死某个 LLM API

Builder 与模型供应商解耦。推荐：

1. `export_zh_template.py` 生成 CSV。
2. 使用 OpenAI / DeepSeek / 其他模型批处理中文释义。
3. 人工抽检。
4. `build_sqlite.py` 导入最终数据库。

这样更换模型不会影响核心词库构建流程。

## JMdict 匹配

按以下信息打分：

1. word + reading 精确匹配。
2. word 精确匹配。
3. 纯假名通过 reading 匹配。
4. 英文 seed meaning 与 JMdict gloss 词汇重合度。
5. JMdict common priority。

无法匹配或多个候选分差太小时进入：

```text
data/intermediate/manual_review.json
```

宁可人工审核，也不强制绑定错误 Entry。

## SQLite

主要表：

```text
sources
vocabulary
meanings
examples
tags
vocabulary_tags
word_lists
word_list_items
metadata
vocabulary_fts
```

`word_lists` 为未来的“标日初级 / Genki / 大家的日语 / 自定义词书”预留多对多模型。

## iOS

把完整生成后的：

```text
data/output/vocabulary.sqlite
```

加入 Xcode 的 Copy Bundle Resources。

Swift 示例见：

```text
swift/VocabularyRepository.swift
```

推荐把词库作为只读 Bundle DB；用户背词进度另存 Core Data / SwiftData / user.sqlite，通过 vocabulary.id 关联。

## Go

当前 Go CLI 作为 Python Pipeline 的包装层：

```bash
cd go
go run ./cmd/builder -root ..
```

样本：

```bash
go run ./cmd/builder -root .. -sample
```

## 数据源

OpenJLPT：
https://github.com/evanclan/OpenJLPT

JMdict：
https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project

正式发布 App 前，请再次检查各数据源当时最新的授权条款，并在 App 的“关于 / 数据来源与许可证”中完成要求的署名。

## v0.1 已包含

- OpenJLPT N5～N1 下载脚本
- 标准化
- JMdict XML 流式解析
- JMdict 候选匹配
- manual review 队列
- 中文释义 CSV 接口
- SQLite Schema / Builder
- FTS5 表
- 数据校验
- Swift SQLite3 示例
- Go CLI 包装层
- 可直接打开的样本 vocabulary.sqlite
