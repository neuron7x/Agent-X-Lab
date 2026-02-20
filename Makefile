.PHONY: bootstrap fmt fmt-check lint type test validate eval ci precommit

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

eval:
	python scripts/run_object_evals.py --repo-root . --write-evidence

ci: lint type test validate eval

precommit:
	ruff check .
	ruff format --check .
	mypy .
	python -m pytest -q
