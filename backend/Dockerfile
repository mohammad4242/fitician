FROM ghcr.io/astral-sh/uv:0.8.14 AS uv
FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36

COPY --from=uv /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ffmpeg \
        fonts-dejavu-core \
        fonts-vazirmatn \
        libharfbuzz-subset0 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN uv sync --frozen --no-dev \
    && mkdir -p /var/lib/fitician/media

EXPOSE 8000

ARG APP_BUILD_SHA=
ENV APP_BUILD_SHA=${APP_BUILD_SHA}
LABEL org.opencontainers.image.revision=${APP_BUILD_SHA}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
