FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src

ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src

# Default command runs the API; the worker service overrides it.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
