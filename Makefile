.PHONY: bootstrap fmt lint type test validate eval ci precommit

bootstrap:
	python scripts/bootstrap_env.py

fmt:
	ruff format .

lint:
	ruff check .

type:
	mypy .

test:
	python -m pytest -q

validate:
	python scripts/validate_arsenal.py --repo-root . --strict

eval:
	python scripts/run_object_evals.py --repo-root . --write-evidence

ci: lint type test validate eval

precommit:
	ruff check .
	ruff format --check .
	mypy .
	python -m pytest -q
