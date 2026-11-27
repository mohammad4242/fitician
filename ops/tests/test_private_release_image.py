import importlib.util
import io
import json
import tarfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "imagecheck", Path(__file__).parents[1] / "check-private-release-image.py"
)
module = importlib.util.module_from_spec(spec)


def archive(files):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as tar:
        for name, content in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            tar.addfile(member, io.BytesIO(content))
    output.seek(0)
    return output


class ImagePrivacyTests(unittest.TestCase):
    def test_checks_every_layer_even_when_a_later_layer_removes_the_map(self):
        spec.loader.exec_module(module)
        old = archive(
            {"usr/share/nginx/html/assets/app.js.map": b"private source"}
        ).getvalue()
        new = archive({"usr/share/nginx/html/assets/.wh.app.js.map": b""}).getvalue()
        image = archive(
            {
                "manifest.json": json.dumps(
                    [{"Layers": ["old.tar", "new.tar"], "Config": "config.json"}]
                ).encode(),
                "old.tar": old,
                "new.tar": new,
                "config.json": b"{}",
            }
        )
        with self.assertRaisesRegex(ValueError, "private_source_map"):
            module.check_archive(image, [])

    def test_finds_privileged_credential_across_stream_chunks_without_printing_it(self):
        spec.loader.exec_module(module)
        secret = b"private-token-fixture"
        layer = archive(
            {"usr/share/nginx/html/assets/app.js": b"x" * 65530 + secret + b"y" * 10}
        ).getvalue()
        image = archive(
            {
                "manifest.json": json.dumps(
                    [{"Layers": ["layer.tar"], "Config": "config.json"}]
                ).encode(),
                "layer.tar": layer,
                "config.json": b"{}",
            }
        )
        with self.assertRaisesRegex(ValueError, "privileged_credential") as failure:
            module.check_archive(image, [secret])
        self.assertNotIn(secret.decode(), str(failure.exception))
