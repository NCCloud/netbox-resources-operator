# The image is greatly inspired by this article
# https://hynek.me/articles/docker-uv/
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS build

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync \
        --locked \
        --no-dev \
        --no-install-project

COPY . /app
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache \
    uv sync \
        --locked \
        --no-dev \
        --no-editable

##########################################################################

FROM python:3.13-alpine

ENV PATH=/app/.venv/bin:$PATH

RUN addgroup -S operator && adduser -S operator -G operator

COPY --from=build --chown=operator:operator /app /app

USER operator
WORKDIR /app

CMD ["kopf", "run", "main.py", "--verbose", "-A"]
