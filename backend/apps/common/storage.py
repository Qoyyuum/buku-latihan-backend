"""
Thin wrapper over boto3 for the S3-compatible bucket (Cloudflare R2 in
production, MinIO locally).

All object access goes through short-lived presigned URLs so the bucket can
stay fully private — no public-read configuration needed on R2.
"""

import uuid
from typing import Any

import boto3
from django.conf import settings

_PUT_TTL_SECONDS = 15 * 60


def _client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def new_key(prefix: str, filename: str) -> str:
    """Generate a unique object key like ``prefix/<uuid>__filename``."""
    safe_name = filename.replace(" ", "_")[-120:]
    return f"{prefix.strip('/')}/{uuid.uuid4()}__{safe_name}"


def presign_put(key: str, content_type: str) -> str:
    """Presigned URL a client PUTs a file to directly."""
    return _client().generate_presigned_url(  # type: ignore[no-any-return]
        "put_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=_PUT_TTL_SECONDS,
    )


def presign_get(key: str, ttl: int | None = None) -> str:
    """Presigned URL a client GETs an object with."""
    return _client().generate_presigned_url(  # type: ignore[no-any-return]
        "get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": key,
        },
        ExpiresIn=ttl or settings.WORKSHEET_URL_TTL_SECONDS,
    )


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    """Server-side write — used for stroke JSON and composited pages."""
    _client().put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


def get_bytes(key: str) -> bytes:
    response = _client().get_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=key,
    )
    return response["Body"].read()  # type: ignore[no-any-return]
