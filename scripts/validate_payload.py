#!/usr/bin/env python3
"""Validate a Feishu Doc XML payload before publication."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


INLINE_TAGS = {"a", "b", "br", "del", "em", "latex", "span", "u"}
BLOCK_TAGS = {
    "blockquote",
    "callout",
    "checkbox",
    "code",
    "col",
    "colgroup",
    "column",
    "figure",
    "grid",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "source",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "title",
    "tr",
    "ul",
    "whiteboard",
}
HEADING_TAGS = {f"h{level}" for level in range(1, 10)}
ALLOWED_TAGS = INLINE_TAGS | BLOCK_TAGS | HEADING_TAGS

BASIC_COLORS = {"red", "orange", "yellow", "green", "blue", "purple", "gray"}
LIGHT_COLORS = {f"light-{color}" for color in BASIC_COLORS}
MEDIUM_COLORS = {f"medium-{color}" for color in BASIC_COLORS}
TEXT_BACKGROUNDS = BASIC_COLORS | LIGHT_COLORS | {"medium-gray"}
CALLOUT_BACKGROUNDS = {"gray"} | LIGHT_COLORS | MEDIUM_COLORS
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
RESOURCE_TAGS = {"img", "source", "whiteboard"}
DISALLOWED_CALLOUT_DESCENDANTS = {
    "blockquote",
    "callout",
    "figure",
    "grid",
    "hr",
    "img",
    "pre",
    "source",
    "table",
    "whiteboard",
}
EMOJI_RE = re.compile(
    "[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF]",
    flags=re.UNICODE,
)


class PayloadValidationError(ValueError):
    """Raised when a payload cannot be parsed or violates the contract."""


@dataclass
class ValidationResult:
    valid: bool
    title: Optional[str]
    top_level_blocks: int
    total_elements: int
    text_characters: int
    resource_count: int
    errors: List[str]
    warnings: List[str]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_fragment(xml_text: str) -> ET.Element:
    if not xml_text.strip():
        raise PayloadValidationError("payload is empty")
    if "<!DOCTYPE" in xml_text.upper() or "<!ENTITY" in xml_text.upper():
        raise PayloadValidationError("DOCTYPE and ENTITY declarations are not allowed")
    try:
        return ET.fromstring(f"<feishu-document>{xml_text}</feishu-document>")
    except ET.ParseError as exc:
        raise PayloadValidationError(f"invalid XML: {exc}") from exc


def _resolved_local_path(raw: str, base_dir: Path) -> Tuple[Optional[Path], Optional[str]]:
    if not raw.startswith("@./"):
        return None, "local resource paths must start with @./"
    candidate = (base_dir / raw[3:]).resolve()
    try:
        candidate.relative_to(base_dir.resolve())
    except ValueError:
        return None, "local resource path escapes --base-dir"
    if not candidate.is_file():
        return None, f"local resource does not exist: {raw}"
    return candidate, None


def _validate_colors(element: ET.Element, tag: str, errors: List[str]) -> None:
    for attr in ("text-color", "border-color"):
        value = element.attrib.get(attr)
        if value and value not in BASIC_COLORS:
            errors.append(f"<{tag}> has invalid {attr}: {value}")

    background = element.attrib.get("background-color")
    if not background:
        return
    allowed = CALLOUT_BACKGROUNDS if tag == "callout" else TEXT_BACKGROUNDS
    if tag not in {"callout", "span", "td", "th"}:
        errors.append(f"<{tag}> does not support background-color in this skill")
    elif background not in allowed:
        errors.append(f"<{tag}> has invalid background-color: {background}")


def _validate_resource(
    element: ET.Element,
    tag: str,
    base_dir: Path,
    errors: List[str],
) -> None:
    if tag == "img":
        locations = [key for key in ("path", "href", "src") if element.attrib.get(key)]
        if len(locations) != 1:
            errors.append("<img> requires exactly one of path, href, or src")
            return
        location = locations[0]
    elif tag == "source":
        locations = [key for key in ("path", "token") if element.attrib.get(key)]
        if len(locations) != 1:
            errors.append("<source> requires exactly one of path or token")
            return
        location = locations[0]
    else:
        locations = [key for key in ("path", "src", "type") if element.attrib.get(key)]
        if not locations and not (element.text or "").strip():
            errors.append("<whiteboard> requires type, src, path, or inline content")
            return
        location = "path" if element.attrib.get("path") else ""

    if location == "path":
        raw = element.attrib["path"]
        resolved, error = _resolved_local_path(raw, base_dir)
        if error:
            errors.append(f"<{tag}> {error}")
            return
        if tag == "img" and resolved:
            if resolved.suffix.lower() not in IMAGE_SUFFIXES:
                errors.append(f"<img> has unsupported file type: {resolved.suffix}")
            if resolved.stat().st_size > 20 * 1024 * 1024:
                errors.append(f"<img> exceeds the 20 MiB limit: {raw}")
    elif location == "href":
        parsed = urlparse(element.attrib["href"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append("<img href> must use an absolute HTTP(S) URL")


def _iter_with_ancestors(root: ET.Element) -> Iterable[Tuple[ET.Element, Tuple[str, ...]]]:
    def walk(node: ET.Element, ancestors: Tuple[str, ...]) -> Iterable[Tuple[ET.Element, Tuple[str, ...]]]:
        for child in list(node):
            tag = _local_name(child.tag)
            yield child, ancestors
            yield from walk(child, ancestors + (tag,))

    return walk(root, tuple())


def validate_xml(xml_text: str, base_dir: Path) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    title: Optional[str] = None

    try:
        root = parse_fragment(xml_text)
    except PayloadValidationError as exc:
        return ValidationResult(False, None, 0, 0, 0, 0, [str(exc)], [])

    top_level = list(root)
    title_elements = [element for element in top_level if _local_name(element.tag) == "title"]
    if len(title_elements) != 1:
        errors.append("payload must contain exactly one top-level <title>")
    else:
        title = "".join(title_elements[0].itertext()).strip()
        if not title:
            errors.append("<title> cannot be empty")
        if top_level and top_level[0] is not title_elements[0]:
            errors.append("<title> must be the first top-level block")

    heading_levels: List[int] = []
    text_characters = 0
    resource_count = 0
    callout_count = 0
    highlight_characters = 0
    divider_count = 0
    emoji_count = 0

    for element, ancestors in _iter_with_ancestors(root):
        tag = _local_name(element.tag)
        if tag not in ALLOWED_TAGS:
            errors.append(f"unsupported tag: <{tag}>")
            continue

        _validate_colors(element, tag, errors)
        text = "".join(element.itertext()).strip()
        if tag not in INLINE_TAGS:
            text_characters += len((element.text or "").strip())
        emoji_count += len(EMOJI_RE.findall(element.text or ""))

        if tag in HEADING_TAGS:
            heading_levels.append(int(tag[1:]))
            if not text:
                errors.append(f"<{tag}> cannot be empty")
        if tag == "callout":
            callout_count += 1
            if "callout" in ancestors:
                errors.append("callouts cannot be nested")
            for descendant in element.iter():
                descendant_tag = _local_name(descendant.tag)
                if descendant is not element and descendant_tag in DISALLOWED_CALLOUT_DESCENDANTS:
                    errors.append(f"<callout> cannot contain <{descendant_tag}>")
        if tag == "span" and element.attrib.get("background-color"):
            highlight_characters += len(text)
        if tag == "hr":
            divider_count += 1
        if tag in RESOURCE_TAGS:
            resource_count += 1
            _validate_resource(element, tag, base_dir, errors)

    for previous, current in zip(heading_levels, heading_levels[1:]):
        if current > previous + 1:
            errors.append(f"heading hierarchy jumps from h{previous} to h{current}")

    content_blocks = [
        element
        for element in top_level
        if _local_name(element.tag) not in {"title", "hr"}
    ]
    if not content_blocks:
        errors.append("payload contains no document body blocks")

    if callout_count > 3:
        warnings.append("Minimal Editorial recommends no more than three callouts")
    if divider_count > 4:
        warnings.append("Minimal Editorial recommends no more than four dividers")
    if text_characters and highlight_characters / text_characters > 0.08:
        warnings.append("highlighted text exceeds 8% of document text")
    if emoji_count > 6:
        warnings.append("document uses more than six emoji")
    if heading_levels and max(heading_levels) > 4:
        warnings.append("heading depth exceeds h4")

    total_elements = sum(1 for _ in root.iter()) - 1
    return ValidationResult(
        valid=not errors,
        title=title,
        top_level_blocks=len(top_level),
        total_elements=total_elements,
        text_characters=text_characters,
        resource_count=resource_count,
        errors=errors,
        warnings=warnings,
    )


def validate_file(path: Path, base_dir: Optional[Path] = None) -> ValidationResult:
    source = path.resolve()
    resolved_base = (base_dir or source.parent).resolve()
    return validate_xml(source.read_text(encoding="utf-8"), resolved_base)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path, help="Feishu XML payload file")
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Base directory for @./ local resource paths; defaults to the payload directory",
    )
    parser.add_argument("--strict", action="store_true", help="Treat design warnings as errors")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = validate_file(args.payload, args.base_dir)
    except (OSError, UnicodeError) as exc:
        result = ValidationResult(False, None, 0, 0, 0, 0, [str(exc)], [])

    output = asdict(result)
    if args.strict and result.warnings:
        output["valid"] = False
        output["errors"] = result.errors + [f"strict: {item}" for item in result.warnings]
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
