FROM node:22.18.0-bookworm-slim AS node-runtime

FROM python:3.12-slim-bookworm AS tools-builder

ARG AGY_VERSION=1.5.14
ARG AGY_SHA256_AMD64=d58386322d2073e96b33f7cc32b4e9ae2db6228f58440369725967b2de48c7b5
ARG AGY_SHA256_ARM64=e5f69a3123fac66974b303d9a201f381a0fb32b3ef869d9139da85d5caf67a2a
ARG CODEX_VERSION=0.151.0
ARG CLAUDE_VERSION=2.1.220
ARG TARGETARCH

ENV PATH=/opt/fitician-agent/bin:$PATH \
    AGY_CLI_DISABLE_AUTO_UPDATE=true \
    CLAUDE_CODE_DISABLE_AUTOUPDATE=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

RUN set -eux; \
    case "${TARGETARCH:-amd64}" in \
      amd64) agy_arch="x64"; agy_sha256="${AGY_SHA256_AMD64}" ;; \
      arm64) agy_arch="arm64"; agy_sha256="${AGY_SHA256_ARM64}" ;; \
      *) echo "Unsupported Antigravity architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    mkdir -p /opt/fitician-agent/bin; \
    agy_archive="/tmp/agy.tar.gz"; \
    curl --fail --silent --show-error --location --retry 3 \
      "https://github.com/google-antigravity/antigravity-cli/releases/download/${AGY_VERSION}/agy_cli_linux_${agy_arch}.tar.gz" \
      --output "${agy_archive}"; \
    echo "${agy_sha256}  ${agy_archive}" | sha256sum --check --status; \
    mkdir -p /tmp/agy-extract; \
    tar --extract --gzip --file "${agy_archive}" --directory /tmp/agy-extract; \
    agy_binary="$(find /tmp/agy-extract -type f \( -name agy -o -name antigravity \) -print -quit)"; \
    test -n "${agy_binary}"; \
    install -m 0755 -o root -g root "${agy_binary}" /opt/fitician-agent/bin/agy; \
    rm -rf /tmp/agy-extract "${agy_archive}"; \
    test "$(agy --version | head -n 1)" = "${AGY_VERSION}"; \
    npm install --global --no-audit --no-fund --cache /tmp/npm-cache --prefix /opt/fitician-agent @openai/codex@${CODEX_VERSION}; \
    test "$(codex --version | head -n 1)" = "codex-cli ${CODEX_VERSION}"; \
    npm install --global --no-audit --no-fund --cache /tmp/npm-cache --prefix /opt/fitician-agent @anthropic-ai/claude-code@${CLAUDE_VERSION}; \
    test "$(claude --version | head -n 1)" = "${CLAUDE_VERSION} (Claude Code)"; \
    rm -rf /tmp/npm-cache /root/.npm; \
    chown -R root:root /opt/fitician-agent; \
    chmod -R go-w /opt/fitician-agent

FROM python:3.12-slim-bookworm AS python-builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

FROM python:3.12-slim-bookworm

ENV HOME=/home/agent \
    PATH=/opt/fitician-agent/bin:/home/agent/.local/bin:/app/.venv/bin:/opt/venv/bin:$PATH \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    AGY_CLI_DISABLE_AUTO_UPDATE=true \
    CLAUDE_CODE_DISABLE_AUTOUPDATE=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl dbus git gnome-keyring \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash agent

COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=tools-builder --chown=root:root /opt/fitician-agent /opt/fitician-agent

WORKDIR /app
COPY --from=python-builder /app/.venv /app/.venv
COPY --chmod=0755 docker/entrypoint.sh /usr/local/bin/fitician-agent-entrypoint
COPY app ./app

USER agent

ARG APP_BUILD_SHA=
ENV APP_BUILD_SHA=${APP_BUILD_SHA}
LABEL org.opencontainers.image.revision=${APP_BUILD_SHA}

EXPOSE 9001
ENTRYPOINT ["/usr/local/bin/fitician-agent-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9001"]
