# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.8.14 AS uv
FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36 AS python
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install --no-install-recommends -y git ffmpeg fonts-dejavu-core libharfbuzz-subset0 libpango-1.0-0 libpangoft2-1.0-0 && rm -rf /var/lib/apt/lists/*
COPY backend/pyproject.toml backend/uv.lock /deps/backend/
COPY agent-service/pyproject.toml agent-service/uv.lock /deps/agent-service/
RUN uv sync --project /deps/backend --frozen --extra dev --no-install-project \
    && uv sync --project /deps/agent-service --frozen --group dev --no-install-project
COPY backend/app/__init__.py /policy/app/__init__.py
COPY backend/app/debugging/__init__.py backend/app/debugging/ci_contract.py \
     backend/app/debugging/tools.py backend/app/debugging/privacy.py /policy/app/debugging/
COPY docker/debug-validation/entrypoint.py /policy/entrypoint.py
ARG POLICY_SHA
LABEL io.fitician.validation-policy=${POLICY_SHA}
USER 10001:10001
ENTRYPOINT ["python", "/policy/entrypoint.py"]

FROM node:20.19.4-bookworm-slim AS node
FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36 AS frontend
RUN apt-get update && apt-get install --no-install-recommends -y libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
WORKDIR /deps
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package.json
COPY packages/fitician-core/package.json packages/fitician-core/package.json
COPY vendor vendor
RUN npm ci --ignore-scripts \
    && rm node_modules/@fitician/core \
    && ln -s /workspace/packages/fitician-core node_modules/@fitician/core
COPY backend/app/__init__.py /policy/app/__init__.py
COPY backend/app/debugging/__init__.py backend/app/debugging/ci_contract.py \
     backend/app/debugging/tools.py backend/app/debugging/privacy.py /policy/app/debugging/
COPY docker/debug-validation/entrypoint.py /policy/entrypoint.py
ARG POLICY_SHA
LABEL io.fitician.validation-policy=${POLICY_SHA}
USER 10001:10001
ENTRYPOINT ["python3", "/policy/entrypoint.py"]
