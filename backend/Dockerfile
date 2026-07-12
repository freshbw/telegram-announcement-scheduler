FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
        UV_LINK_MODE=copy \
        PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl \
        && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM base AS runtime

COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000