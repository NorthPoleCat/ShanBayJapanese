PYTHON ?= python3

.PHONY: all download normalize jmdict match refine sense-template enrich \
        translate-senses-openai translate-senses-deepseek audit-senses \
        db validate build sample clean

all: build

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

translate-senses-openai:
	$(PYTHON) scripts/translate_senses_zh.py --provider openai --model $${OPENAI_MODEL}

translate-senses-deepseek:
	$(PYTHON) scripts/translate_senses_zh.py --provider deepseek --model $${DEEPSEEK_MODEL}

audit-senses:
	$(PYTHON) scripts/audit_senses.py

enrich:
	$(PYTHON) scripts/enrich_learning_data.py

db:
	$(PYTHON) scripts/build_sqlite.py

validate:
	$(PYTHON) scripts/validate.py --strict-counts

build: download normalize jmdict match refine sense-template
	@echo ""
	@echo "Translate/fill zh_senses.csv, then:"
	@echo "  make audit-senses"
	@echo "  make enrich"
	@echo "  make db"
	@echo "  make validate"

sample:
	$(PYTHON) scripts/build_sample.py

clean:
	rm -rf data/intermediate/* data/output/*
