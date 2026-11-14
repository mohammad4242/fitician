import hashlib
import io
import json
import tarfile

import pytest


def archive(*, invalid_config_path=False, multiple=False):
    config = json.dumps(
        {
            "architecture": "amd64",
            "os": "linux",
            "config": {"Env": ["PRIVATE_TEST_FIXTURE=not-for-output"]},
            "rootfs": {"type": "layers", "diff_ids": ["sha256:" + "a" * 64]},
        }
    ).encode()
    digest = hashlib.sha256(config).hexdigest()
    name = "0" * 64 + ".json" if invalid_config_path else digest + ".json"
    manifest = [{"Config": name, "RepoTags": ["local:fixture"], "Layers": ["layer.tar"]}]
    if multiple:
        manifest *= 2
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as stream:
        for path, value in [
            (name, config),
            ("layer.tar", b"untrusted-layer-fixture"),
            ("manifest.json", json.dumps(manifest).encode()),
        ]:
            info = tarfile.TarInfo(path)
            info.size = len(value)
            stream.addfile(info, io.BytesIO(value))
    output.seek(0)
    return output, "sha256:" + digest


def test_canonical_identity_uses_verified_config_bytes_instead_of_the_store_specific_id():
    from app.debugging.image_identity import canonical_config_digest

    stream, expected = archive()
    assert canonical_config_digest(stream) == expected


@pytest.mark.parametrize("options", [{"invalid_config_path": True}, {"multiple": True}])
def test_modified_or_ambiguous_config_is_rejected_without_exporting_its_content(options):
    from app.debugging.image_identity import canonical_config_digest

    stream, _ = archive(**options)
    with pytest.raises(ValueError) as caught:
        canonical_config_digest(stream)
    assert "PRIVATE_TEST_FIXTURE" not in str(caught.value)


def oci_archive(*, corrupt_descriptor=False):
    # Containerd can retain descriptors without the original unpacked config blob.
    config_digest = "sha256:" + "b" * 64
    image = json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "digest": config_digest,
                "size": 200,
            },
            "layers": [],
        }
    ).encode()
    image_digest = hashlib.sha256(image).hexdigest()
    descriptor = {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "digest": "sha256:" + ("c" * 64 if corrupt_descriptor else image_digest),
        "size": len(image),
        "platform": {"os": "linux", "architecture": "amd64"},
    }
    index = json.dumps({"schemaVersion": 2, "manifests": [descriptor]}).encode()
    index_digest = hashlib.sha256(index).hexdigest()
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as stream:
        for path, value in [
            ("blobs/sha256/" + image_digest, image),
            ("blobs/sha256/" + index_digest, index),
            (
                "index.json",
                json.dumps(
                    {
                        "schemaVersion": 2,
                        "manifests": [
                            {
                                "digest": "sha256:" + index_digest,
                                "size": len(index),
                                "mediaType": "application/vnd.oci.image.index.v1+json",
                            }
                        ],
                    }
                ).encode(),
            ),
            ("manifest.json", json.dumps([{"Config": "blobs/sha256/" + "b" * 64}]).encode()),
        ]:
            item = tarfile.TarInfo(path)
            item.size = len(value)
            stream.addfile(item, io.BytesIO(value))
    output.seek(0)
    return output, config_digest


def test_containerd_config_identity_follows_only_hash_verified_platform_descriptors():
    from app.debugging.image_identity import canonical_config_digest

    stream, expected = oci_archive()
    assert canonical_config_digest(stream) == expected
    stream, _ = oci_archive(corrupt_descriptor=True)
    with pytest.raises(ValueError):
        canonical_config_digest(stream)
