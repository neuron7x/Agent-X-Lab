SHELL := /usr/bin/env bash
PY := python

.DEFAULT_GOAL := help

help:
	@echo "AgentX Lab dev targets:"
	@echo "  make setup        - create venv and install dev deps"
	@echo "  make format       - auto-format (ruff)"
	@echo "  make lint         - ruff + actionlint + schema checks"
	@echo "  make typecheck    - mypy"
	@echo "  make test         - pytest"
	@echo "  make validate     - validate arsenal invariants"
	@echo "  make eval         - run object eval harnesses"
	@echo "  make ci           - run lint+typecheck+test+validate+eval"
	@echo "  make rebuild      - rebuild MANIFEST checksums + catalogs"

.venv:
	$(PY) -m venv .venv
	. .venv/bin/activate && $(PY) -m pip install --upgrade pip

setup: .venv
	. .venv/bin/activate && $(PY) -m pip install -r requirements-dev.txt
	. .venv/bin/activate && pre-commit install

format:
	$(PY) -m ruff format .

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
	actionlint -color
	$(PY) scripts/schema_validate.py --repo-root .

typecheck:
	$(PY) -m mypy scripts tests

test:
	$(PY) -m pytest --cov --cov-report=term-missing

validate:
	$(PY) scripts/validate_arsenal.py --repo-root . --strict

eval:
	$(PY) scripts/run_object_evals.py --repo-root .

ci: lint typecheck test validate eval

rebuild:
	$(PY) scripts/rebuild_checksums.py --repo-root .
	$(PY) scripts/rebuild_catalog_index.py --repo-root .
