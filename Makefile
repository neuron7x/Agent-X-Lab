PYTHONHASHSEED ?= 0
export PYTHONHASHSEED
LC_ALL ?= C
export LC_ALL
LANG ?= C
export LANG
TZ ?= UTC
export TZ
PYTHONDONTWRITEBYTECODE ?= 1
export PYTHONDONTWRITEBYTECODE
GIT_PAGER ?= cat
export GIT_PAGER
PAGER ?= cat
export PAGER

.PHONY: \
	setup bootstrap fmt format_check fmt-check lint type typecheck test validate eval evals \
	protocol inventory readme_contract proof proof-verify check verify all demo ci precommit doctor quickstart clean reset vuln-scan workflow-hygiene action-pinning check_r8 release-artifacts verify-release-integrity

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
	python tools/derive_proof.py --evidence artifacts/agent/evidence.jsonl --out artifacts/agent/proof.json

proof-verify:
	python tools/derive_proof.py --evidence artifacts/agent/evidence.jsonl --out artifacts/agent/proof.derived.json
	cmp -s artifacts/agent/proof.derived.json artifacts/agent/proof.json

vuln-scan:
	python tools/pip_audit_gate.py --requirements requirements.lock --requirements requirements-dev.txt --allowlist policies/pip_audit_allowlist.json --out artifacts/security/pipaudit.json

workflow-hygiene:
	python tools/verify_workflow_hygiene.py

action-pinning:
	python tools/verify_action_pinning.py

check_r8: check
	python tools/feg_r8_verify.py

check: doctor format_check lint typecheck test validate evals protocol inventory readme_contract workflow-hygiene action-pinning

verify: check


release-artifacts:
	mkdir -p artifacts/release
	tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner -czf artifacts/release/agentx-lab.tar.gz MANIFEST.json README.md VR.json protocol.yaml
	sha256sum artifacts/release/agentx-lab.tar.gz > artifacts/release/checksums.txt
	python -c "import json;from pathlib import Path;release=Path('artifacts/release');cyclonedx={'bomFormat':'CycloneDX','specVersion':'1.5','version':1,'components':[]};spdx={'SPDXID':'SPDXRef-DOCUMENT','creationInfo':{'created':'1970-01-01T00:00:00Z','creators':['Tool: manual-generator']},'dataLicense':'CC0-1.0','documentNamespace':'https://example.invalid/spdx/agentx-lab','name':'agentx-lab','spdxVersion':'SPDX-2.3'};predicate={'buildDefinition':{'buildType':'https://slsa.dev/container-based-build/v1','externalParameters':{'ref':'local'},'resolvedDependencies':[]},'runDetails':{'builder':{'id':'https://github.com/Agent-X-Lab/.github/workflows/release.yml'},'metadata':{'finishedOn':'1970-01-01T00:00:00Z','invocationId':'local','startedOn':'1970-01-01T00:00:00Z'}}};statement={'_type':'https://in-toto.io/Statement/v1','predicate':predicate,'predicateType':'https://slsa.dev/provenance/v1','subject':[{'digest':{'sha256':'local'},'name':'agentx-lab.tar.gz'}]};(release/'sbom.cyclonedx.json').write_text(json.dumps(cyclonedx,sort_keys=True,indent=2)+'\\n',encoding='utf-8');(release/'sbom.spdx.json').write_text(json.dumps(spdx,sort_keys=True,indent=2)+'\\n',encoding='utf-8');(release/'provenance-predicate.json').write_text(json.dumps(predicate,sort_keys=True,indent=2)+'\\n',encoding='utf-8');(release/'provenance.intoto.jsonl').write_text(json.dumps(statement,sort_keys=True)+'\\n',encoding='utf-8');(release/'agentx-lab.tar.gz.sig').write_text('local-signature\\n',encoding='utf-8')"

verify-release-integrity:
	python tools/verify_release_integrity.py --release-dir artifacts/release

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
