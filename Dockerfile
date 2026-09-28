FROM python:3.12-slim

# uv installs deps much faster than pip and reads our existing pyproject.toml/uv.lock directly
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY evals ./evals

ENV PYTHONPATH=/app
EXPOSE 8000
# Call the venv's uvicorn directly, not `uv run` - `uv run` re-syncs the environment (incl. dev
# deps like ruff) on every container start, needing network access and wasting the image build.
# Found by actually running `docker compose up` rather than assuming the build was enough.
CMD [".venv/bin/uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
