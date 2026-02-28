.PHONY: setup bootstrap lint test test-all test-integration test-e2e test-property dev-ui dev-worker gates reproduce repo-model

PYTHON ?= python
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
PYTHON_RUN := $(PYTHON)

setup:
	npm ci
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r engine/requirements-dev.txt

bootstrap: setup
	bash scripts/bootstrap.sh

lint:
	npm run lint
	$(PYTHON_RUN) -m compileall -q engine udgs_core

test:
	npm test
	$(PYTHON_RUN) -m pytest engine udgs_core

test-all: test

test-integration:
	$(PYTHON_RUN) -m pytest -m integration engine udgs_core

test-e2e:
	npm run test:e2e

test-property:
	$(PYTHON_RUN) -m pytest -m property engine udgs_core

dev-ui:
	npm run dev

dev-worker:
	npm --prefix workers/axl-bff run dev

gates:
	$(PYTHON_RUN) engine/scripts/check_prod_spec_gates.py \
		--ac artifacts/AC_VERSION.json \
		--pb-dir ad2026_state/pb \
		--ssdf artifacts/SSDF.map \
		--artifacts-dir artifacts \
		--out build_proof/prod_spec/gate_check.report.json

reproduce: test
	mkdir -p artifacts/proof_bundle
	$(PYTHON_RUN) scripts/generate_manifest.py


repo-model:
	mkdir -p engine/artifacts/repo_model
	PYTHONPATH=engine $(PYTHON_RUN) -m exoneural_governor repo-model
