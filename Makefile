.PHONY: all paper audit baseline-check check core-test model-test rtl-test integration-test scalar-test packed-test packed-integration-test

all: check paper

paper:
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error -file-line-error paper/main_es.tex
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error -file-line-error paper/main_en.tex
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error -file-line-error paper/main.tex

core-test:
	python3 kuntur/verification/run.py

model-test:
	python3 scripts/verify_model.py

rtl-test:
	python3 scripts/verify_rtl.py

integration-test:
	python3 scripts/verify_integration.py

scalar-test:
	python3 scripts/verify_scalar.py

packed-test:
	python3 scripts/verify_packed.py

packed-integration-test:
	python3 scripts/verify_packed_integration.py

audit:
	python3 scripts/audit_core.py

baseline-check:
	python3 scripts/audit_core.py --verify-only

check: baseline-check
	python3 scripts/check_project.py
