.PHONY: bootstrap test lint dev-ui dev-worker gates

bootstrap:
	bash scripts/bootstrap.sh

lint:
	npm run lint
	.venv/bin/python -m compileall -q engine udgs_core

test:
	npm test
	.venv/bin/python -m pytest engine udgs_core

dev-ui:
	npm run dev

dev-worker:
	npm --prefix workers/axl-bff run dev

gates:
	.venv/bin/python engine/scripts/check_prod_spec_gates.py \
		--ac artifacts/AC_VERSION.json \
		--pb-dir ad2026_state/pb \
		--ssdf artifacts/SSDF.map \
		--artifacts-dir artifacts \
		--out build_proof/prod_spec/gate_check.report.json
