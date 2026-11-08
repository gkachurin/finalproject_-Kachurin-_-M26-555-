.PHONY: install run format lint check clean

install:
	uv sync

run:
	uv run main.py

format:
	uv run ruff format .

lint:
	uv run ruff check .

check: format lint

clean:
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
