from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path


class RedisComposeContractTests(unittest.TestCase):
    workspace = Path(__file__).resolve().parents[2]
    redis_image = (
        "redis:8.10.1-alpine@"
        "sha256:becdda6c7f4b3fb42e42fd7f120bbf5c54c4caaaf16f26da24e4563d2c1f0576"
    )

    def _compose_config(self, compose_file: str, **values: str) -> dict[str, object]:
        environment = os.environ.copy()
        environment.update(values)
        result = subprocess.run(
            ["docker", "compose", "-f", compose_file, "config", "--format", "json"],
            cwd=self.workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_local_redis_is_digest_pinned_authenticated_and_loopback_only(self) -> None:
        config = self._compose_config("compose.yaml")
        redis = config["services"]["redis"]

        self.assertEqual(redis["image"], self.redis_image)
        self.assertEqual(redis["ports"][0]["host_ip"], "127.0.0.1")
        self.assertEqual(redis["ports"][0]["published"], "6379")
        self.assertTrue(
            any(
                volume["type"] == "volume"
                and volume["source"] == "fitician_redis_data"
                and volume["target"] == "/data"
                for volume in redis["volumes"]
            )
        )
        self.assertTrue(
            any(
                volume["type"] == "bind"
                and volume["target"] == "/usr/local/etc/redis/redis.conf"
                and volume["read_only"]
                for volume in redis["volumes"]
            )
        )
        self.assertIn("--requirepass", " ".join(redis["command"]))
        self.assertIn("REDISCLI_AUTH", redis["healthcheck"]["test"][-1])

    def test_production_redis_has_no_host_port_and_persistent_storage(self) -> None:
        config = self._compose_config(
            "compose.prod.yaml",
            DOCKERHUB_USERNAME="example",
            IMAGE_TAG="0" * 40,
            POSTGRES_PASSWORD="postgres-test-password",
            DATABASE_URL="postgresql+psycopg://fitician:secret@db:5432/fitician",
            FITICIAN_DOMAIN="fitician.example",
            REDIS_PASSWORD="redis-test-password",
            AGENT_SERVICE_TOKEN="agent-test-token",
        )
        redis = config["services"]["redis"]

        self.assertEqual(redis["image"], self.redis_image)
        self.assertNotIn("ports", redis)
        self.assertIn("expose", redis)
        self.assertTrue(
            any(
                volume["type"] == "volume"
                and volume["source"] == "fitician_prod_redis_data"
                and volume["target"] == "/data"
                for volume in redis["volumes"]
            )
        )

    def test_redis_policy_requires_aof_every_second_and_noeviction(self) -> None:
        config = (self.workspace / "ops/redis/redis.conf").read_text()

        self.assertIn("appendonly yes", config)
        self.assertIn("appendfsync everysec", config)
        self.assertIn("aof-use-rdb-preamble yes", config)
        self.assertIn("maxmemory 128mb", config)
        self.assertIn("maxmemory-policy noeviction", config)

    def test_backends_do_not_wait_for_optional_redis_health(self) -> None:
        local = self._compose_config("compose.yaml")
        production = self._compose_config(
            "compose.prod.yaml",
            DOCKERHUB_USERNAME="example",
            IMAGE_TAG="0" * 40,
            POSTGRES_PASSWORD="postgres-test-password",
            DATABASE_URL="postgresql+psycopg://fitician:secret@db:5432/fitician",
            FITICIAN_DOMAIN="fitician.example",
            REDIS_PASSWORD="redis-test-password",
            AGENT_SERVICE_TOKEN="agent-test-token",
        )

        for config in (local, production):
            for service_name in ("backend", "backend-2"):
                if service_name not in config["services"]:
                    continue
                dependencies = config["services"][service_name].get("depends_on", {})
                self.assertNotIn("redis", dependencies)


if __name__ == "__main__":
    unittest.main()
