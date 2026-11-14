import importlib.util
import io
import json
import subprocess
import tarfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

SPEC = importlib.util.spec_from_file_location(
    "debug_validation", Path(__file__).parents[1] / "debug-validation.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
ci_contract = __import__("app.debugging.ci_contract", fromlist=["test_result"])


class DebugValidationTests(unittest.TestCase):
    def test_nutrition_audit_uses_the_same_isolated_postgres_without_host_configuration(self):
        name = "fitician-validation-" + str(uuid4())
        args = runner.container_command(
            name, "sha256:" + "a" * 64, Path("/source"), "backend",
            ["backend/tests/nutrition/test_food_photo_estimation.py"], network=name,
        )
        self.assertIn(
            "--env=NUTRITION_AUDIT_DATABASE_URL="
            "postgresql+psycopg://fitician:fitician_ci@db:5432/fitician_nutrition_audit",
            args,
        )

    def test_child_environment_preserves_only_isolated_synthetic_database_urls(self):
        script = Path(__file__).parents[2] / "docker/debug-validation/sandbox_environment.py"
        spec = importlib.util.spec_from_file_location("sandbox_environment", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        main = "postgresql+psycopg://fitician:fitician_ci@db:5432/fitician_test"
        audit = main.removesuffix("fitician_test") + "fitician_nutrition_audit"
        result = module.child_environment(Path("/workspace/backend"), "/deps/bin", {
            "DATABASE_URL": main, "TEST_DATABASE_URL": main,
            "NUTRITION_AUDIT_DATABASE_URL": audit,
            "GITHUB_TOKEN": "must-not-leak", "SENTRY_DSN": "must-not-leak",
        })
        self.assertEqual(result["NUTRITION_AUDIT_DATABASE_URL"], audit)
        self.assertEqual(result["SENTRY_DSN"], "")
        self.assertNotIn("GITHUB_TOKEN", result)
        self.assertEqual(result["TMPDIR"], "/scratch")
        with self.assertRaisesRegex(ValueError, "isolated_database_required"):
            module.child_environment(Path("/workspace/backend"), "/deps/bin", {
                "DATABASE_URL": "postgresql://production.invalid/private",
            })

    def test_dependency_packages_stay_linked_while_build_caches_are_writable(self):
        script = (
            Path(__file__).parents[2] / "docker/debug-validation/dependency_links.py"
        )
        spec = importlib.util.spec_from_file_location("dependency_links", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory(dir=Path(__file__).parents[2] / ".codex-tmp") as temp:
            root = Path(temp)
            source = root / "deps"
            (source / "@scope/package").mkdir(parents=True)
            (source / ".tmp").mkdir()
            (source / "typescript").mkdir()
            target = root / "workspace/node_modules"
            module.link_dependencies(source, target)
            self.assertTrue((target / "typescript").is_symlink())
            self.assertTrue((target / "@scope/package").is_symlink())
            (target / ".tmp").mkdir()
            (target / ".tmp/cache").write_text("ephemeral")
            self.assertFalse((source / ".tmp/cache").exists())

    def test_compiler_resolution_uses_the_frontend_workspace_dependencies(self):
        with TemporaryDirectory(dir=Path(__file__).parents[2] / ".codex-tmp") as temp:
            workspace = Path(temp)
            package = workspace / "frontend/node_modules/typescript"
            (package / "bin").mkdir(parents=True)
            (package / "package.json").write_text(
                '{"name":"typescript","version":"fixture"}'
            )
            (package / "bin/tsc").write_text(
                'console.log(JSON.stringify({source:"nested",args:process.argv.slice(2)}))'
            )
            script = Path(__file__).parents[2] / "docker/debug-validation/node-tool.cjs"
            response = subprocess.run(
                ["node", str(script), "typescript", "--version"],
                cwd=workspace / "frontend",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(response.returncode, 0, response.stderr)
            self.assertEqual(
                json.loads(response.stdout), {"source": "nested", "args": ["--version"]}
            )

    def test_container_has_no_host_authority_credentials_or_external_network(self):
        name = "fitician-validation-" + str(uuid4())
        args = runner.container_command(
            name,
            "sha256:" + "a" * 64,
            Path("/source"),
            "backend",
            ["backend/tests/test_debug_runs.py"],
            network=name,
        )
        self.assertIn("--read-only", args)
        self.assertIn("--cap-drop=ALL", args)
        self.assertIn("--security-opt=no-new-privileges", args)
        self.assertIn("--user=10001:10001", args)
        self.assertIn("--memory=2g", args)
        self.assertIn("--memory-swap=2g", args)
        self.assertIn("--tmpfs=/scratch:uid=10001,gid=10001,mode=0700,size=3g", args)
        self.assertIn("--pids-limit=128", args)
        self.assertIn("--network=" + name, args)
        self.assertIn("type=bind,src=/source,dst=/source,readonly", args)
        text = json.dumps(args)
        for forbidden in [
            "docker.sock",
            "--privileged",
            "GITHUB_TOKEN",
            "SENTRY_AUTH_TOKEN",
            "/root",
            "host.docker.internal",
        ]:
            self.assertNotIn(forbidden, text)
        self.assertNotIn(
            "--network=" + name,
            runner.container_command(
                name,
                "sha256:" + "a" * 64,
                Path("/source"),
                "agent",
                ["agent-service/tests/test_api.py"],
            ),
        )

    def test_archive_rejects_symlinks_and_escape_paths(self):
        with TemporaryDirectory(dir=Path(__file__).parents[2] / ".codex-tmp") as temp:
            root = Path(temp)
            for name, link in [("../outside.py", False), ("backend/app/link.py", True)]:
                archive = root / "source.tar"
                with tarfile.open(archive, "w") as output:
                    item = tarfile.TarInfo(name)
                    if link:
                        item.type = tarfile.SYMTYPE
                        item.linkname = "/etc/passwd"
                    else:
                        item.size = 1
                    output.addfile(item, None if link else io.BytesIO(b"x"))
                with self.assertRaisesRegex(ValueError, "unsafe_candidate_archive"):
                    runner.extract_source(archive, root / "checkout")

    def test_result_requires_exercised_tests_and_zero_failures(self):
        with TemporaryDirectory(dir=Path(__file__).parents[2] / ".codex-tmp") as temp:
            path = Path(temp) / "results.xml"
            for xml, valid in [
                (
                    '<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0"/></testsuites>',
                    True,
                ),
                (
                    '<testsuites><testsuite tests="2" failures="1" errors="0"/></testsuites>',
                    False,
                ),
                ('<testsuites><testsuite tests="2" skipped="2"/></testsuites>', False),
                ("<testsuites/>", False),
                ("invalid", False),
            ]:
                path.write_text(xml)
                self.assertEqual(
                    ci_contract.test_result(path)["exercised"] > 0
                    and ci_contract.test_result(path)["failures"] == 0,
                    valid,
                )
