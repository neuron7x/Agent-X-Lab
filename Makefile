.PHONY: setup bootstrap fmt fmt-check lint type test validate eval proof ci precommit

export PYTHONHASHSEED := 0

setup:
	python -m pip install -r requirements.lock
	python -m pip install -r requirements-dev.txt

bootstrap:
	python scripts/bootstrap_env.py

fmt:
	ruff format .

fmt-check:
	ruff format --check .

lint:
	ruff check .

type:
	mypy .

test:
	python -m pytest -q -W error

validate:
	python scripts/validate_arsenal.py --repo-root . --strict
	python tools/verify_protocol_consistency.py --protocol protocol.yaml
	python tools/titan9_inventory.py --repo-root . --out artifacts/titan9/inventory.json
	python tools/verify_readme_contract.py --readme README.md --workflows .github/workflows --inventory artifacts/titan9/inventory.json

proof:
	python tools/generate_titan9_proof.py --repo-root .

eval:
	python scripts/run_object_evals.py --repo-root . --write-evidence

ci: fmt-check lint type test validate eval proof

precommit:
	ruff check .
	ruff format --check .
	mypy .
	python -m pytest -q
