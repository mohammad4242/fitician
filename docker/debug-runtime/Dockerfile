# syntax=docker/dockerfile:1.7
FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36 AS codex
RUN mkdir /build && python - <<'PY'
import hashlib, pathlib, urllib.request
url = 'https://github.com/openai/codex/releases/download/rust-v0.167.2/codex-x86_64-unknown-linux-musl.tar.gz'
digest = hashlib.sha256()
size = 0
with urllib.request.urlopen(url, timeout=60) as response, pathlib.Path('/build/codex.tar.gz').open('wb') as output:
    while chunk := response.read(1048576):
        size += len(chunk)
        assert size <= 130000000, 'Codex artifact exceeds size limit'
        digest.update(chunk)
        output.write(chunk)
assert digest.hexdigest() == '8246e846c550ea21197fcc4067bc270dca895e94ea42ed6a282e6f4e0125b15f', 'Codex artifact checksum mismatch'
PY
RUN python -c "import os,pathlib,tarfile; t=tarfile.open('/build/codex.tar.gz'); p=pathlib.Path('/usr/local/bin/codex'); p.write_bytes(t.extractfile('codex-x86_64-unknown-linux-musl').read()); p.chmod(0o755); os.utime(p,(0,0))" \
    && python -c "import subprocess; assert subprocess.check_output(['/usr/local/bin/codex','--version'],text=True).strip() == 'codex-cli 0.167.2'"

FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::https::Timeout=20 -o Acquire::Retries=1 update \
    && DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::https::Timeout=20 -o Acquire::Retries=1 install --no-install-recommends -y git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 debug-runtime \
    && useradd --uid 10001 --gid 10001 --home-dir /state --no-create-home debug-runtime \
    && mkdir /state \
    && chown 10001:10001 /state \
    && chmod 0700 /state
COPY docker/debug-runtime/requirements.lock /build/requirements.lock
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r /build/requirements.lock \
    && rm -rf /build
COPY --from=codex /usr/local/bin/codex /usr/local/bin/codex
WORKDIR /app
COPY backend/app/__init__.py /app/app/__init__.py
COPY backend/app/debugging/__init__.py backend/app/debugging/appserver.py \
     backend/app/debugging/catalog.py backend/app/debugging/connector.py \
     backend/app/debugging/github.py backend/app/debugging/limits.py \
     backend/app/debugging/privacy.py backend/app/debugging/runtime_storage.py \
     backend/app/debugging/server_runtime.py backend/app/debugging/tools.py \
     backend/app/debugging/workspaces.py backend/app/debugging/ci_contract.py \
     backend/app/debugging/github_automation.py backend/app/debugging/automation_client.py /app/app/debugging/
ARG APP_BUILD_SHA
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOME=/state CODEX_HOME=/state/codex \
    FITICIAN_RUNTIME_COMMIT=${APP_BUILD_SHA}
LABEL org.opencontainers.image.revision=${APP_BUILD_SHA}
USER 10001:10001
ENTRYPOINT ["python", "-m", "app.debugging.server_runtime"]
CMD ["serve"]
