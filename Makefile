PYTHONHASHSEED ?= 0
export PYTHONHASHSEED

.PHONY: \
	setup bootstrap fmt format_check fmt-check lint type typecheck test validate eval evals \
	protocol inventory readme_contract proof check verify all demo ci precommit doctor quickstart clean reset

setup:
	python -m pip install -r requirements.lock
	python -m pip install -r requirements-dev.txt

bootstrap: setup

doctor:
	python tools/doctor.py

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

check: doctor format_check lint typecheck test validate evals protocol inventory readme_contract

verify: check

demo: proof

quickstart:
	sh scripts/quickstart.sh

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf artifacts/titan9 artifacts/evidence artifacts/release

reset: clean
	rm -rf .venv

all: setup check proof

ci: check

precommit: format_check lint typecheck test
