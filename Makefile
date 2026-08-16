.NOTPARALLEL: reproduce
.PHONY: inputs test pipeline validation llm schelling figures paper-tables paper reproduce clean

PYTHON ?= python3

inputs:
	$(PYTHON) scripts/check_inputs.py

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

pipeline: inputs
	$(PYTHON) scripts/run_pipeline.py

validation: inputs
	$(PYTHON) scripts/score_goldset.py
	$(PYTHON) scripts/validation_robustness.py
	$(PYTHON) scripts/draw_random_sample.py
	$(PYTHON) scripts/circuit_split.py

llm: inputs
	$(PYTHON) scripts/score_llm_baseline.py
	$(PYTHON) scripts/analyze_prevalence.py

paper-tables:
	$(PYTHON) scripts/make_paper_tables.py

schelling: pipeline
	$(PYTHON) scripts/run_schelling.py

figures: validation llm schelling
	$(PYTHON) scripts/make_paper_figures.py
	$(PYTHON) scripts/make_paper_figures_house.py

paper: figures paper-tables
	cd paper && latexmk -pdf -bibtex -interaction=nonstopmode -halt-on-error fha443.tex
	$(PYTHON) paper/check_rulers.py paper/fha443.pdf

reproduce: inputs test pipeline validation llm schelling figures paper-tables

clean:
	rm -rf outputs data/processed/case_features.csv data/processed/analysis_panel.csv \
	  data/processed/feii_panel.csv data/processed/doctrine_map.csv \
	  data/processed/doctrine_divergence.csv data/processed/doctrine_transitions.csv \
	  data/raw/synthetic_corpus.jsonl data/external/synthetic_housing_panel.csv \
	  data/processed/_synth_truth.json .pytest_cache
