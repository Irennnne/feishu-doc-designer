#!/usr/bin/env python3
"""Safely publish a validated Feishu Doc XML payload through lark-cli."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

from validate_payload import ValidationResult, parse_fragment, validate_xml


class PublishError(RuntimeError):
    """A sanitized publication failure suitable for user-facing output."""


def _serialize_fragment(root: ET.Element) -> str:
    return "\n".join(ET.tostring(child, encoding="unicode") for child in list(root)) + "\n"


def _stage_payload(xml_text: str, base_dir: Path, staging_dir: Path) -> Tuple[Path, int]:
    root = parse_fragment(xml_text)
    assets_dir = staging_dir / "assets"
    staged = 0
    copied: Dict[Path, str] = {}

    for element in root.iter():
        raw = element.attrib.get("path")
        if not raw:
            continue
        source = (base_dir / raw[3:]).resolve()
        if source not in copied:
            digest = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:10]
            safe_name = source.name.replace(" ", "-")
            relative = f"assets/{digest}-{safe_name}"
            assets_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, staging_dir / relative)
            copied[source] = relative
            staged += 1
        element.set("path", f"@./{copied[source]}")

    payload_path = staging_dir / "document.xml"
    payload_path.write_text(_serialize_fragment(root), encoding="utf-8")
    return payload_path, staged


def _extract_json(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise PublishError("lark-cli returned no JSON output")
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    candidates = []
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            value, consumed = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append((consumed, -index, value))
    if candidates:
        return max(candidates, key=lambda item: (item[0], item[1]))[2]
    raise PublishError("lark-cli returned output that could not be parsed as JSON")


def _error_detail(payload: Dict[str, Any]) -> str:
    error = payload.get("error")
    if not isinstance(error, dict):
        return "lark-cli reported an unsuccessful operation"
    parts = []
    for key in ("code", "type", "message"):
        if error.get(key) is not None:
            parts.append(f"{key}={error[key]}")
    detail = error.get("detail")
    if isinstance(detail, dict) and detail.get("log_id"):
        parts.append(f"log_id={detail['log_id']}")
    return ", ".join(parts) or "lark-cli reported an unsuccessful operation"


def _document_from_response(response: Dict[str, Any]) -> Dict[str, Any]:
    if response.get("ok") is not True:
        raise PublishError(_error_detail(response))
    data = response.get("data")
    if not isinstance(data, dict):
        raise PublishError("lark-cli response has no data object")
    warnings = response.get("warnings") or data.get("warnings")
    if warnings:
        raise PublishError("lark-cli returned degradation warnings; publication was not accepted")
    document = data.get("document")
    if not isinstance(document, dict):
        raise PublishError("lark-cli response has no document object")
    document_id = document.get("document_id") or document.get("token")
    url = document.get("url") or document.get("doc_url") or data.get("url")
    if not document_id:
        raise PublishError("lark-cli reported success without a document id")
    if not url:
        raise PublishError("lark-cli reported success without a document URL")
    return document


def _build_command(args: argparse.Namespace) -> list:
    command = [
        args.lark_cli,
        "docs",
        "+create",
        "--as",
        "user",
        "--doc-format",
        "xml",
        "--content",
        "@./document.xml",
    ]
    if args.folder_token:
        command.extend(["--parent-token", args.folder_token])
    elif args.wiki_node:
        command.extend(["--parent-token", args.wiki_node])
    elif args.wiki_space:
        command.extend(["--parent-position", args.wiki_space])
    return command


def publish(args: argparse.Namespace) -> Dict[str, Any]:
    payload_path = args.payload.resolve()
    base_dir = (args.base_dir or payload_path.parent).resolve()
    xml_text = payload_path.read_text(encoding="utf-8")
    validation = validate_xml(xml_text, base_dir)
    if not validation.valid:
        raise PublishError("payload validation failed: " + "; ".join(validation.errors))

    with tempfile.TemporaryDirectory(prefix="feishu-doc-designer-") as temp:
        staging_dir = Path(temp)
        _, staged_assets = _stage_payload(xml_text, base_dir, staging_dir)
        command = _build_command(args)

        if args.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "title": validation.title,
                "expected_blocks": validation.top_level_blocks,
                "staged_assets": staged_assets,
                "validation_warnings": validation.warnings,
                "command": command[:-1] + ["@./document.xml"],
            }

        executable = shutil.which(args.lark_cli) if os.sep not in args.lark_cli else args.lark_cli
        if not executable or not Path(executable).exists():
            raise PublishError(
                "lark-cli is not installed; follow references/publishing.md for the official setup"
            )

        completed = subprocess.run(
            command,
            cwd=staging_dir,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            check=False,
            shell=False,
        )
        if completed.returncode != 0:
            try:
                response = _extract_json(completed.stdout or completed.stderr)
                raise PublishError(_error_detail(response))
            except PublishError as exc:
                if "could not be parsed" not in str(exc) and "no JSON" not in str(exc):
                    raise
                raise PublishError(f"lark-cli exited with status {completed.returncode}") from None

        response = _extract_json(completed.stdout)
        document = _document_from_response(response)
        new_blocks = document.get("new_blocks")
        return {
            "ok": True,
            "dry_run": False,
            "title": validation.title,
            "document_id": document.get("document_id") or document.get("token"),
            "url": document.get("url") or document.get("doc_url") or response["data"].get("url"),
            "expected_blocks": validation.top_level_blocks,
            "created_blocks": len(new_blocks) if isinstance(new_blocks, list) else None,
            "staged_assets": staged_assets,
            "validation_warnings": validation.warnings,
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path, help="Validated Feishu XML payload")
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Base directory for @./ resources; defaults to the payload directory",
    )
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--folder-token")
    destination.add_argument("--wiki-node")
    destination.add_argument("--wiki-space")
    parser.add_argument("--dry-run", action="store_true", help="Validate and stage without calling Feishu")
    parser.add_argument("--lark-cli", default="lark-cli", help=argparse.SUPPRESS)
    parser.add_argument("--timeout", type=int, default=180, help=argparse.SUPPRESS)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = publish(args)
    except (OSError, UnicodeError, subprocess.TimeoutExpired, PublishError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
