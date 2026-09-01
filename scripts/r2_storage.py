#!/usr/bin/env python3
"""Dependency-free Cloudflare R2 S3-compatible presigning helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import os
import re
from urllib.parse import quote, urlsplit, urlunsplit
import uuid


MAX_PRESIGN_SECONDS = 7 * 24 * 60 * 60
DEFAULT_PRESIGN_SECONDS = 24 * 60 * 60
SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9_.-]+")


class R2ConfigurationError(ValueError):
    """Raised when the local R2 configuration is incomplete or unsafe."""


def _required(name: str, value: str | None) -> str:
    if not value:
        raise R2ConfigurationError(f"{name} is required for --r2")
    return value


def _safe_component(value: str) -> str:
    normalized = SAFE_COMPONENT.sub("-", value).strip(".-")
    return normalized or "bundle"


def _encoded_query(parameters: dict[str, str]) -> str:
    encoded = [
        (quote(key, safe="-_.~"), quote(value, safe="-_.~"))
        for key, value in parameters.items()
    ]
    return "&".join(f"{key}={value}" for key, value in sorted(encoded))


def _hmac(key: bytes, value: str) -> bytes:
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()


@dataclass(frozen=True)
class R2Storage:
    """R2 bucket configuration and AWS Signature Version 4 presigner."""

    endpoint_url: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    prefix: str = "manim-render"
    url_expiry_seconds: int = DEFAULT_PRESIGN_SECONDS

    def __post_init__(self) -> None:
        parsed = urlsplit(self.endpoint_url.rstrip("/"))
        if parsed.scheme != "https" or not parsed.netloc:
            raise R2ConfigurationError("R2_ENDPOINT_URL must be an HTTPS origin")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise R2ConfigurationError("R2_ENDPOINT_URL must not contain a path or query")
        if not self.bucket or "/" in self.bucket:
            raise R2ConfigurationError("R2_BUCKET must be a non-empty bucket name")
        if not self.access_key_id or not self.secret_access_key:
            raise R2ConfigurationError("R2 access credentials are required for --r2")
        if not 1 <= self.url_expiry_seconds <= MAX_PRESIGN_SECONDS:
            raise R2ConfigurationError(
                f"R2 URL expiry must be between 1 and {MAX_PRESIGN_SECONDS} seconds"
            )
        if any(part in {".", ".."} for part in self.prefix.split("/")):
            raise R2ConfigurationError("R2_PREFIX must not contain '.' or '..' path components")

    @classmethod
    def from_args(cls, args: object) -> "R2Storage":
        bucket = getattr(args, "r2_bucket", None) or os.environ.get("R2_BUCKET")
        endpoint_url = getattr(args, "r2_endpoint_url", None) or os.environ.get("R2_ENDPOINT_URL")
        account_id = os.environ.get("R2_ACCOUNT_ID")
        if not endpoint_url and account_id:
            endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        access_key_id = os.environ.get("R2_ACCESS_KEY_ID")
        secret_access_key = os.environ.get("R2_SECRET_ACCESS_KEY")
        prefix = getattr(args, "r2_prefix", None)
        if prefix is None:
            prefix = os.environ.get("R2_PREFIX", "manim-render")
        expiry = getattr(args, "r2_url_expiry_seconds", None)
        if expiry is None:
            raw_expiry = os.environ.get("R2_URL_EXPIRY_SECONDS")
            expiry = int(raw_expiry) if raw_expiry else DEFAULT_PRESIGN_SECONDS
        return cls(
            endpoint_url=_required("R2_ENDPOINT_URL or R2_ACCOUNT_ID", endpoint_url),
            bucket=_required("R2_BUCKET", bucket),
            access_key_id=_required("R2_ACCESS_KEY_ID", access_key_id),
            secret_access_key=_required("R2_SECRET_ACCESS_KEY", secret_access_key),
            prefix=str(prefix).strip("/"),
            url_expiry_seconds=int(expiry),
        )

    def new_batch_id(self, label: str, now: datetime | None = None) -> str:
        current = now or datetime.now(timezone.utc)
        timestamp = current.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{_safe_component(label)}-{timestamp}-{uuid.uuid4().hex[:12]}"

    def object_key(self, batch_id: str, *parts: str) -> str:
        components = [self.prefix, _safe_component(batch_id)] if self.prefix else [_safe_component(batch_id)]
        for part in parts:
            if not part or "/" in part or part in {".", ".."}:
                raise R2ConfigurationError("R2 object path components must be simple names")
            components.append(part)
        return "/".join(components)

    def presign(self, method: str, key: str, *, now: datetime | None = None) -> str:
        method = method.upper()
        if method not in {"GET", "PUT", "DELETE"}:
            raise R2ConfigurationError("R2 presigning supports only GET, PUT, and DELETE")
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise R2ConfigurationError("R2 object key must be relative and safe")

        endpoint = urlsplit(self.endpoint_url.rstrip("/"))
        host = endpoint.netloc
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        amz_date = current.strftime("%Y%m%dT%H%M%SZ")
        short_date = current.strftime("%Y%m%d")
        scope = f"{short_date}/auto/s3/aws4_request"
        canonical_uri = "/" + quote(self.bucket, safe="-_.~") + "/" + quote(key, safe="/-_.~")
        parameters = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.access_key_id}/{scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(self.url_expiry_seconds),
            "X-Amz-SignedHeaders": "host",
        }
        canonical_query = _encoded_query(parameters)
        canonical_headers = f"host:{host}\n"
        canonical_request = "\n".join(
            (method, canonical_uri, canonical_query, canonical_headers, "host", "UNSIGNED-PAYLOAD")
        )
        string_to_sign = "\n".join(
            ("AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical_request.encode()).hexdigest())
        )
        date_key = _hmac(("AWS4" + self.secret_access_key).encode("utf-8"), short_date)
        region_key = _hmac(date_key, "auto")
        service_key = _hmac(region_key, "s3")
        signing_key = _hmac(service_key, "aws4_request")
        parameters["X-Amz-Signature"] = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return urlunsplit((endpoint.scheme, host, canonical_uri, _encoded_query(parameters), ""))

    def put_url(self, key: str, *, now: datetime | None = None) -> str:
        return self.presign("PUT", key, now=now)

    def get_url(self, key: str, *, now: datetime | None = None) -> str:
        return self.presign("GET", key, now=now)

    def delete_url(self, key: str, *, now: datetime | None = None) -> str:
        return self.presign("DELETE", key, now=now)
