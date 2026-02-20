.PHONY: bootstrap test vr release validate

bootstrap:
	python -m pip install -r requirements.lock

validate:
	sg --config configs/sg.config.json validate-catalog

test:
	python -m pytest -q

vr:
	sg --config configs/sg.config.json vr

release:
	sg --config configs/sg.config.json release
