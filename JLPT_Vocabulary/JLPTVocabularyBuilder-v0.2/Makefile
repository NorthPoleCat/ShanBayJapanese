PYTHON ?= python3

.PHONY: all download normalize jmdict match zh-template translate-openai translate-deepseek audit-zh estimate-zh db validate build sample clean
all: build
download:
	$(PYTHON) scripts/download_sources.py
normalize:
	$(PYTHON) scripts/normalize_jlpt.py
jmdict:
	$(PYTHON) scripts/parse_jmdict.py
match:
	$(PYTHON) scripts/match_jmdict.py
zh-template:
	$(PYTHON) scripts/export_zh_template.py
translate-openai:
	$(PYTHON) scripts/translate_zh.py --provider openai

translate-deepseek:
	$(PYTHON) scripts/translate_zh.py --provider deepseek

audit-zh:
	$(PYTHON) scripts/audit_zh.py

estimate-zh:
	$(PYTHON) scripts/estimate_translation.py

db:
	$(PYTHON) scripts/build_sqlite.py
validate:
	$(PYTHON) scripts/validate.py --strict-counts
build: download normalize jmdict match zh-template
	@echo "Fill data/intermediate/zh_meanings.csv, then run: make db validate"
sample:
	$(PYTHON) scripts/build_sample.py
clean:
	rm -rf data/intermediate/* data/output/*
