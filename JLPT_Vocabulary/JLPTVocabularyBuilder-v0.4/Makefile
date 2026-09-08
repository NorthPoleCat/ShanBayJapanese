PYTHON ?= python3
.PHONY: download normalize jmdict match refine sense-template audit-senses db validate build sample clean

download:
	$(PYTHON) scripts/download_sources.py
normalize:
	$(PYTHON) scripts/normalize_jlpt.py
jmdict:
	$(PYTHON) scripts/parse_jmdict.py
match:
	$(PYTHON) scripts/match_jmdict.py
refine:
	$(PYTHON) scripts/refine_lexicon.py
sense-template:
	$(PYTHON) scripts/export_sense_zh_template.py
audit-senses:
	$(PYTHON) scripts/audit_senses.py
db:
	$(PYTHON) scripts/build_sqlite.py
validate:
	$(PYTHON) scripts/validate.py --strict-counts
build: download normalize jmdict match refine sense-template
	@echo "Translate/fill data/intermediate/zh_senses.csv, then: make audit-senses db validate"
sample:
	$(PYTHON) scripts/build_sample.py
clean:
	rm -rf data/intermediate/* data/output/*

translate-senses-openai:
	$(PYTHON) scripts/translate_senses_zh.py --provider openai --model $${OPENAI_MODEL}
translate-senses-deepseek:
	$(PYTHON) scripts/translate_senses_zh.py --provider deepseek --model $${DEEPSEEK_MODEL}
