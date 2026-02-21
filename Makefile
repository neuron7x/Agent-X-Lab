PYTHONHASHSEED ?= 0
export PYTHONHASHSEED

.PHONY: \
	help clean setup bootstrap fmt format_check fmt-check lint type typecheck test validate eval evals \
	protocol inventory readme_contract proof check verify all demo ci precommit

help:
	@printf "%s\n" "Available targets:"
	@printf "%s\n" "  make setup          Install runtime and dev dependencies"
	@printf "%s\n" "  make check          Run full deterministic validation suite"
	@printf "%s\n" "  make proof          Generate titan9 proof artifacts"
	@printf "%s\n" "  make all            setup + check + proof"
	@printf "%s\n" "  make clean          Remove generated local artifacts"

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache

setup:
	python -m pip install -r requirements.lock
	python -m pip install -r requirements-dev.txt

bootstrap: setup

fmt:
	ruff format .

format_check:
	ruff format --check .

fmt-check: format_check

lint:
	ruff check .

typecheck:
	mypy .

type: typecheck

test:
	python -m pytest -q -W error

validate:
	python scripts/validate_arsenal.py --repo-root . --strict

evals:
	python scripts/run_object_evals.py --repo-root . --write-evidence

eval: evals

protocol:
	python tools/verify_protocol_consistency.py --protocol protocol.yaml

inventory:
	python tools/titan9_inventory.py --repo-root . --out artifacts/titan9/inventory.json

readme_contract: inventory
	python tools/verify_readme_contract.py --readme README.md --workflows .github/workflows --inventory artifacts/titan9/inventory.json

proof:
	python tools/generate_titan9_proof.py --repo-root .

check: format_check lint typecheck test validate evals protocol inventory readme_contract

verify: check

demo: proof

all: setup check proof

ci: check

precommit: format_check lint typecheck test
