.PHONY: install demo monitor test lint clean

install:
	python -m pip install -e ".[dev]"

demo:
	python -m infra_monitor --config config/config.example.yaml demo --reset

monitor:
	python -m infra_monitor --config config/config.example.yaml monitor --cycles 1

test:
	pytest

lint:
	ruff check src tests scripts

clean:
	python scripts/clean_generated.py

