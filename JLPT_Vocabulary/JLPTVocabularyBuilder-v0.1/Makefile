PYTHON ?= python3

.PHONY: all download normalize jmdict match zh-template db validate build sample clean
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
