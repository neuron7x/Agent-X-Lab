.PHONY: bootstrap fmt lint type test validate eval ci precommit

bootstrap:
	python -m pip install -r requirements.lock
	python -m pip install -r requirements-dev.txt

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
	pre-commit run --all-files
