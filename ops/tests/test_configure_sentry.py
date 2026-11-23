import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "configure_sentry", Path(__file__).parents[1] / "configure-sentry.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SetupTests(unittest.TestCase):
    def test_existing_projects_are_reused_and_only_public_dsns_are_exported(self):
        requests = []

        def request(method, path, body=None):
            requests.append((method, path, body))
            if path == "/api/0/organizations/fitician/":
                return {"slug": "fitician"}
            if path.endswith("/keys/"):
                return [
                    {
                        "isActive": True,
                        "dsn": {
                            "public": "https://public@example.invalid/1",
                            "secret": "DO_NOT_EXPORT",
                        },
                    }
                ]
            if method == "PUT":
                return {**body, "isPublic": False}
            return {"id": "1", "slug": path.rstrip("/").split("/")[-1], "isPublic": False}

        setup = module.SentrySetup(request, "fitician", "fitician")
        result = setup.configure(apply=True)
        self.assertEqual(len(result), 4)
        self.assertNotIn("DO_NOT_EXPORT", str(result))
        self.assertFalse(any(method == "POST" for method, _, _ in requests))
        self.assertTrue(
            all(
                body["storeCrashReports"] == 0 and body["dataScrubber"]
                for method, _, body in requests
                if method == "PUT"
            )
        )
