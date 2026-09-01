"""Offline tests for the dependency-free Cloudflare R2 integration."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class R2StorageTests(unittest.TestCase):
    def test_presign_is_sigv4_and_does_not_expose_secret(self) -> None:
        r2 = load_module("r2_storage_test", ROOT / "scripts" / "r2_storage.py")
        storage = r2.R2Storage(
            endpoint_url="https://account-id.r2.cloudflarestorage.com",
            bucket="render-bucket",
            access_key_id="access-key",
            secret_access_key="secret-value",
            prefix="manim-render",
            url_expiry_seconds=3600,
        )
        url = storage.put_url(
            "manim-render/20260901/job/chunk-0000.tar.gz",
            now=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        parsed = urlsplit(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "account-id.r2.cloudflarestorage.com")
        self.assertEqual(parsed.path, "/render-bucket/manim-render/20260901/job/chunk-0000.tar.gz")
        self.assertEqual(query["X-Amz-Algorithm"], ["AWS4-HMAC-SHA256"])
        self.assertEqual(query["X-Amz-Expires"], ["3600"])
        self.assertIn("X-Amz-Signature", query)
        self.assertNotIn("secret-value", url)

        delete_url = storage.delete_url(
            "manim-render/20260901/job/chunk-0000.tar.gz",
            now=datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(parse_qs(urlsplit(delete_url).query)["X-Amz-Algorithm"], ["AWS4-HMAC-SHA256"])

    def test_object_keys_reject_path_traversal(self) -> None:
        r2 = load_module("r2_storage_key_test", ROOT / "scripts" / "r2_storage.py")
        storage = r2.R2Storage(
            endpoint_url="https://account-id.r2.cloudflarestorage.com",
            bucket="render-bucket",
            access_key_id="access-key",
            secret_access_key="secret-value",
        )
        with self.assertRaises(ValueError):
            storage.object_key("job", "../output.tar.gz")

    def test_from_args_builds_endpoint_from_account_id(self) -> None:
        r2 = load_module("r2_storage_env_test", ROOT / "scripts" / "r2_storage.py")
        args = type(
            "Args",
            (),
            {
                "r2_bucket": None,
                "r2_endpoint_url": None,
                "r2_prefix": None,
                "r2_url_expiry_seconds": None,
            },
        )()
        with patch.dict(
            "os.environ",
            {
                "R2_ACCOUNT_ID": "account-id",
                "R2_BUCKET": "render-bucket",
                "R2_ACCESS_KEY_ID": "access-key",
                "R2_SECRET_ACCESS_KEY": "secret-value",
            },
            clear=True,
        ):
            storage = r2.R2Storage.from_args(args)
        self.assertEqual(storage.endpoint_url, "https://account-id.r2.cloudflarestorage.com")
        self.assertEqual(storage.bucket, "render-bucket")


if __name__ == "__main__":
    unittest.main()
