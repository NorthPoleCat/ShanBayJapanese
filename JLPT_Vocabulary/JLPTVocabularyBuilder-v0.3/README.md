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

## v0.2：中文释义自动批处理

新增 `scripts/translate_zh.py`。它会直接读取并原地更新：

```text
data/intermediate/zh_meanings.csv
```

### OpenAI

```bash
export OPENAI_API_KEY="..."
make translate-openai
```

可覆盖模型：

```bash
python3 scripts/translate_zh.py \
  --provider openai \
  --model gpt-5-mini \
  --batch-size 20
```

### DeepSeek

```bash
export DEEPSEEK_API_KEY="..."
make translate-deepseek
```

或者：

```bash
python3 scripts/translate_zh.py \
  --provider deepseek \
  --model deepseek-chat \
  --batch-size 20
```

### 断点续传

每成功一批，程序都会把结果写回 CSV。所以中途停止后再次执行，只会继续处理 `meaning_zh` 为空的行。

失败批次会记录到：

```text
data/intermediate/zh_failed.jsonl
```

默认单批最多重试 4 次，并使用指数退避。

### 先看 Prompt 数据，不实际调用 API

```bash
python3 scripts/translate_zh.py --provider openai --dry-run --limit 20
```

### 中文质量审核

```bash
make audit-zh
```

输出：

```text
data/intermediate/zh_review.csv
```

当前自动规则会标出：缺失、义项过多、义项过长、混入英文、疑似整句解释等情况。

### 粗略 Token 规划

```bash
make estimate-zh
```

只用于估算批次数和 token 量，不等同于真实账单。

### 推荐完整流程

```bash
make download
make normalize
make jmdict
make match
make zh-template
make estimate-zh
make translate-openai    # 或 make translate-deepseek
make audit-zh
make db
make validate
```

生产版建议人工检查 `zh_review.csv`，同时随机抽检各等级词汇，再生成最终 App 数据库。

## v0.3：翻译预算与实际用量核账

### 运行前估算

```bash
python3 scripts/estimate_translation.py \
  --batch-size 20 \
  --provider openai \
  --model YOUR_MODEL \
  --input-price-per-million INPUT_PRICE \
  --output-price-per-million OUTPUT_PRICE \
  --currency USD \
  --report-json data/intermediate/translation_estimate.json \
  --batch-report-csv data/intermediate/translation_estimate_batches.csv
```

`estimate_translation.py` 会根据 **实际 `SYSTEM_PROMPT` + 每个待翻译词条的 JSON payload + 预期中文返回 JSON** 估算，而不是简单用字符数除以固定比例。

如果环境已经安装 `tiktoken`，脚本会优先使用对应 tokenizer；没有安装时使用内置的中/日/英混合文本启发式估算，因此仍保持“纯 Python 标准库即可运行”的特性。

单价不写死在项目中，因为模型价格可能变化。把当前供应商页面上的“每 1M input/output tokens”价格作为参数传入即可。

### 重试预算

默认额外预留 3%：

```bash
--retry-rate 0.03
```

可以按你的网络/供应商稳定性修改。

### 翻译时记录真实 usage

新版 `translate_zh.py` 会在 API 返回 usage 时追加写入：

```text
data/intermediate/zh_usage.jsonl
```

每一行保存：

```text
provider
model
batch_index
source_seq
usage
```

因此断点续跑也不会丢失之前的用量数据。

### 运行后核账

```bash
python3 scripts/summarize_usage.py \
  --input-price-per-million INPUT_PRICE \
  --output-price-per-million OUTPUT_PRICE
```

如果模型对 cached input 有单独价格：

```bash
python3 scripts/summarize_usage.py \
  --input-price-per-million INPUT_PRICE \
  --cached-input-price-per-million CACHED_INPUT_PRICE \
  --output-price-per-million OUTPUT_PRICE
```

这样整个中文生产任务可以得到：

```text
事前预计请求数 / token / 成本
            ↓
实际批量翻译
            ↓
真实 input/output/cached token
            ↓
实际成本
```
