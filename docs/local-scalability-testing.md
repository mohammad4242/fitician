# Local multi-instance verification

The local scale overlay runs two FastAPI services behind the existing Caddy
architecture. It is intentionally separate from production Compose and does not
change persistent volumes.

```bash
docker compose -f compose.yaml -f compose.multi.yaml config --quiet
docker compose -f compose.yaml -f compose.multi.yaml up -d --build --wait
bash ops/load/run.sh health
```

For distribution evidence, repeat requests through Caddy and inspect the
opt-in local header:

```bash
for i in $(seq 1 40); do curl -fsSI http://127.0.0.1:8080/livez | grep -i '^X-Fitician-Instance:'; done
```

The expected result is at least two distinct instance values. The same stack is
used for Redis restart, worker restart, replica restart, database recovery, and
Caddy upstream drills:

```bash
bash ops/load/failure-drills.sh all
```

The scripts refuse non-local targets unless an explicit operator override is
provided. They never remove volumes. `compose.multi.yaml` explicitly enables the deterministic
local Body Analysis provider for the API fixture and worker; production settings reject it.
Every drill has a deadline and emits one JSON evidence record only after the required degraded
and recovered states have both been observed.
