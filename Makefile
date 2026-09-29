.PHONY: setup test lint eval bench demo reset-demo up down logs

setup:  ## Install deps and start Postgres
	uv sync
	docker compose up -d postgres

test:  ## Run all unit/integration tests (no live API calls, no cost)
	PYTHONPATH=. uv run pytest -q

lint:  ## Static checks (ruff)
	uv run ruff check .
	uv run ruff format --check .

eval:  ## Run the labeled eval set against the real API (~$0.15, ~2 min) and append a benchmarks.md row
	PYTHONPATH=. uv run python -m evals.run_eval

bench:  ## Show all logged benchmark runs so far
	@cat docs/benchmarks.md

demo:  ## Send the signed demo batch (start the server first: uv run uvicorn app.api:app --port 8000)
	uv run python scripts/send_demo.py

reset-demo:  ## Wipe demo data: database AND Sheet rows together (see scripts/reset_demo.py)
	uv run python scripts/reset_demo.py --yes

up:  ## Build and run the whole stack (app + Postgres) in Docker
	docker compose up --build

down:  ## Stop the stack
	docker compose down

logs:  ## Tail the structured JSON logs
	tail -f logs/app.jsonl
