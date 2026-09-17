"""Construct configured object-storage adapters without exposing credentials."""

from __future__ import annotations

from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]

from app.config import Settings
from app.media.storage import S3ObjectStorage


def build_s3_client(settings: Settings) -> Any:
    if not all(
        (
            settings.s3_endpoint,
            settings.s3_public_bucket or settings.s3_private_bucket or settings.s3_bucket,
            settings.s3_access_key_id,
            settings.s3_secret_access_key,
            settings.s3_region,
        )
    ):
        raise ValueError("Complete S3 configuration is required")
    assert settings.s3_access_key_id is not None
    assert settings.s3_secret_access_key is not None
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        config=Config(
            signature_version="s3v4",
            max_pool_connections=64,
            s3={"addressing_style": "virtual"},
        ),
    )


def build_s3_storage(settings: Settings, *, client: Any | None = None) -> S3ObjectStorage:
    bucket = settings.s3_public_bucket or settings.s3_bucket
    if not bucket or not settings.media_public_base_url:
        raise ValueError("S3 bucket and public media base URL are required")
    return S3ObjectStorage(
        client or build_s3_client(settings),
        bucket=bucket,
        public_base_url=settings.media_public_base_url,
        public_acl=settings.s3_public_object_acl,
        namespace="public",
    )


def build_private_s3_storage(settings: Settings, *, client: Any | None = None) -> S3ObjectStorage:
    if not settings.s3_private_bucket:
        raise ValueError("S3 private bucket is required")
    return S3ObjectStorage(
        client or build_s3_client(settings),
        bucket=settings.s3_private_bucket,
        public_base_url="",
        public_acl="private",
        namespace="private",
    )
