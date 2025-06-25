.PHONY: setup sync test test-cov lint format typecheck build check

init:
	make setup-python

setup-python:
	uv python install 3.12

sync:
	uv sync --dev

test:
	uv run pytest ./

test-cov:
	uv run pytest ./ --cov=fraim --cov-report=xml --cov-report=term-missing

format-check:
	uv run ruff format --check .
	uv run ruff check --select I .

format:
	uv run ruff format .
	uv run ruff check --select I --fix .

lint:
	uv run ruff check .

typecheck:
	uv run mypy fraim/

build:
	uv build

check: format-check typecheck test
