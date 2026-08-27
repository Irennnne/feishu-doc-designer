from __future__ import annotations

import json
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_payload  # noqa: E402


FAKE_CLI = r'''#!/usr/bin/env python3
import json
import os
import sys

with open(os.environ["FAKE_LARK_ARGS"], "w", encoding="utf-8") as handle:
    json.dump(sys.argv[1:], handle)

mode = os.environ.get("FAKE_LARK_MODE", "success")
if mode == "error":
    print(json.dumps({"ok": False, "error": {"code": 1770032, "type": "api_error", "message": "forbidden", "detail": {"log_id": "log-safe"}}}))
    raise SystemExit(2)
if mode == "warning":
    print(json.dumps({"ok": True, "data": {"document": {"document_id": "doc_warn", "url": "https://example.feishu.cn/docx/doc_warn"}, "warnings": [{"degrade_code": 1011}]}}))
    raise SystemExit(0)
if mode == "empty":
    print(json.dumps({"ok": True, "data": {"document": {"document_id": "doc_empty"}}}))
    raise SystemExit(0)

print("diagnostic line")
print(json.dumps({"ok": True, "identity": "user", "data": {"document": {"document_id": "doc_ok", "url": "https://example.feishu.cn/docx/doc_ok", "new_blocks": [{"block_id": "b1"}, {"block_id": "b2"}]}}}))
'''


class PublishPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.payload = self.base / "payload.xml"
        self.payload.write_text(
            "<title>Safe $(touch should-not-exist)</title><h2>Body</h2><p>Text</p>",
            encoding="utf-8",
        )
        self.fake_cli = self.base / "fake-lark-cli"
        self.fake_cli.write_text(FAKE_CLI, encoding="utf-8")
        self.fake_cli.chmod(self.fake_cli.stat().st_mode | stat.S_IXUSR)
        self.args_path = self.base / "args.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _args(self, *extra: str):
        return publish_payload._build_parser().parse_args(
            [str(self.payload), "--base-dir", str(self.base), "--lark-cli", str(self.fake_cli), *extra]
        )

    def test_dry_run_does_not_execute_cli(self) -> None:
        result = publish_payload.publish(self._args("--dry-run"))
        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertFalse(self.args_path.exists())
        self.assertIn("@./document.xml", result["command"])

    def test_publish_uses_argument_vector_user_identity_and_relative_file(self) -> None:
        env = {"FAKE_LARK_ARGS": str(self.args_path), "FAKE_LARK_MODE": "success"}
        with patch.dict(os.environ, env, clear=False):
            result = publish_payload.publish(self._args("--folder-token", "fld_safe"))

        self.assertEqual(result["url"], "https://example.feishu.cn/docx/doc_ok")
        self.assertEqual(result["created_blocks"], 2)
        args = json.loads(self.args_path.read_text(encoding="utf-8"))
        self.assertEqual(
            args,
            [
                "docs",
                "+create",
                "--as",
                "user",
                "--doc-format",
                "xml",
                "--content",
                "@./document.xml",
                "--parent-token",
                "fld_safe",
            ],
        )
        self.assertFalse((self.base / "should-not-exist").exists())

    def test_local_asset_is_staged(self) -> None:
        image = self.base / "image with space.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n")
        self.payload.write_text(
            '<title>Asset</title><p>Text</p><img path="@./image with space.png"/>',
            encoding="utf-8",
        )
        env = {"FAKE_LARK_ARGS": str(self.args_path), "FAKE_LARK_MODE": "success"}
        with patch.dict(os.environ, env, clear=False):
            result = publish_payload.publish(self._args())
        self.assertEqual(result["staged_assets"], 1)

    def test_rejects_api_error_without_dumping_credentials(self) -> None:
        env = {"FAKE_LARK_ARGS": str(self.args_path), "FAKE_LARK_MODE": "error"}
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaisesRegex(publish_payload.PublishError, "code=1770032"):
                publish_payload.publish(self._args())

    def test_rejects_degradation_warning(self) -> None:
        env = {"FAKE_LARK_ARGS": str(self.args_path), "FAKE_LARK_MODE": "warning"}
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaisesRegex(publish_payload.PublishError, "degradation warnings"):
                publish_payload.publish(self._args())

    def test_rejects_success_without_url(self) -> None:
        env = {"FAKE_LARK_ARGS": str(self.args_path), "FAKE_LARK_MODE": "empty"}
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaisesRegex(publish_payload.PublishError, "without a document URL"):
                publish_payload.publish(self._args())

    def test_destination_options_are_mutually_exclusive(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self._args("--folder-token", "folder", "--wiki-space", "space")


if __name__ == "__main__":
    unittest.main()
