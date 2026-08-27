from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_payload import validate_file, validate_xml  # noqa: E402


class ValidatePayloadTests(unittest.TestCase):
    def test_all_expected_examples_are_valid(self) -> None:
        expected = ROOT / "examples" / "expected"
        for path in sorted(expected.glob("*.xml")):
            with self.subTest(path=path.name):
                result = validate_file(path)
                self.assertTrue(result.valid, result.errors)
                self.assertTrue(result.title)
                self.assertGreater(result.top_level_blocks, 1)

    def test_requires_one_nonempty_first_title(self) -> None:
        cases = (
            "<p>body</p>",
            "<title></title><p>body</p>",
            "<p>body</p><title>Late</title>",
            "<title>One</title><title>Two</title><p>body</p>",
        )
        for payload in cases:
            with self.subTest(payload=payload):
                result = validate_xml(payload, ROOT)
                self.assertFalse(result.valid)

    def test_rejects_heading_jump(self) -> None:
        result = validate_xml(
            "<title>Jump</title><h2>Start</h2><p>A</p><h4>Too deep</h4><p>B</p>",
            ROOT,
        )
        self.assertFalse(result.valid)
        self.assertIn("heading hierarchy jumps from h2 to h4", result.errors)

    def test_rejects_unsupported_tag_and_invalid_color(self) -> None:
        result = validate_xml(
            '<title>Bad</title><section><p>Text</p></section><callout background-color="pink"><p>x</p></callout>',
            ROOT,
        )
        self.assertFalse(result.valid)
        self.assertIn("unsupported tag: <section>", result.errors)
        self.assertIn("<callout> has invalid background-color: pink", result.errors)

    def test_rejects_resource_inside_callout(self) -> None:
        result = validate_xml(
            '<title>Bad nesting</title><callout background-color="light-blue"><p>Text</p><img href="https://example.com/a.png"/></callout>',
            ROOT,
        )
        self.assertFalse(result.valid)
        self.assertIn("<callout> cannot contain <img>", result.errors)

    def test_accepts_local_image_within_base_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            image = base / "images" / "shot.png"
            image.parent.mkdir()
            image.write_bytes(b"\x89PNG\r\n\x1a\n")
            result = validate_xml(
                '<title>Image</title><p>Before</p><img path="@./images/shot.png" caption="shot"/>',
                base,
            )
            self.assertTrue(result.valid, result.errors)
            self.assertEqual(result.resource_count, 1)

    def test_rejects_missing_or_escaping_local_resource(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            for raw in ("@./missing.png", "@./../outside.png", "/tmp/absolute.png"):
                with self.subTest(raw=raw):
                    result = validate_xml(
                        f'<title>Image</title><p>Before</p><img path="{raw}"/>',
                        base,
                    )
                    self.assertFalse(result.valid)

    def test_rejects_non_http_remote_image(self) -> None:
        result = validate_xml(
            '<title>Remote</title><p>Before</p><img href="file:///tmp/a.png"/>',
            ROOT,
        )
        self.assertFalse(result.valid)
        self.assertIn("<img href> must use an absolute HTTP(S) URL", result.errors)

    def test_warns_on_excessive_minimal_editorial_styling(self) -> None:
        callouts = "".join(
            f'<callout background-color="light-blue"><p>Item {index}</p></callout>'
            for index in range(4)
        )
        result = validate_xml(f"<title>Warnings</title>{callouts}", ROOT)
        self.assertTrue(result.valid, result.errors)
        self.assertTrue(any("three callouts" in warning for warning in result.warnings))

    def test_code_special_characters_survive_xml_contract(self) -> None:
        result = validate_xml(
            '<title>Code</title><h2>Example</h2><pre lang="python"><code>if a &lt; b and b &gt; 0:\n    print(&quot;a &amp; b&quot;)</code></pre>',
            ROOT,
        )
        self.assertTrue(result.valid, result.errors)

    def test_nested_lists_table_and_mermaid_are_valid(self) -> None:
        payload = """<title>Coverage</title>
<h2>Nested list</h2>
<ol><li>Parent<ul><li>Child</li></ul></li></ol>
<h2>Table</h2>
<table><thead><tr><th background-color="light-gray"><p>Key</p></th></tr></thead><tbody><tr><td><p>值</p></td></tr></tbody></table>
<h2>Diagram</h2>
<whiteboard type="mermaid">graph TD\nA --&gt; B</whiteboard>"""
        result = validate_xml(payload, ROOT)
        self.assertTrue(result.valid, result.errors)
        self.assertEqual(result.resource_count, 1)


if __name__ == "__main__":
    unittest.main()
