.PHONY: install test lint demo reproduce build
install:
	python -m pip install -e '.[dev,excel,columnar,gis]'
test:
	python -m pytest -q
lint:
	python -m ruff check src tests
demo:
	ree demo
reproduce:
	ree reproduce flagship
build:
	python -m build
