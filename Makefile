.PHONY: all paper audit baseline-check check core-test model-test rtl-test integration-test scalar-test packed-test packed-integration-test benchmark-plan-test measurement-test kernel-test freeze-policies materialize pilot campaign

all: check paper

paper:
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error -file-line-error paper/main_es.tex
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error -file-line-error paper/main_en.tex
	latexmk -cd -pdf -interaction=nonstopmode -halt-on-error -file-line-error paper/main.tex
	python3 scripts/check_paper_layout.py

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

campaign:
	python3 scripts/run_campaign.py

pilot:
	python3 scripts/run_pilot.py

materialize:
	python3 scripts/materialize_tensors.py

freeze-policies:
	python3 scripts/freeze_policies.py

kernel-test:
	python3 scripts/verify_kernels.py

measurement-test:
	python3 scripts/verify_measurement.py

benchmark-plan-test:
	python3 -m unittest discover -s tests/benchmarks -p 'test_*.py' -v

audit:
	python3 scripts/audit_core.py

baseline-check:
	python3 scripts/audit_core.py --verify-only

check: baseline-check benchmark-plan-test
	python3 scripts/check_project.py
