---
name: feishu-doc-designer
description: Turn local Markdown into restrained, polished Feishu/Lark Docs and publish them with native document blocks. Use for Markdown-to-Feishu conversion, Feishu document beautification, or requests to upload an .md file as a clean Lark document. Do not use for SEO-writing, existing-document synchronization, or Feishu IM message formatting.
metadata:
  short-description: Publish polished Markdown as native Feishu Docs
---

# Feishu Doc Designer

Publish a local Markdown document as a clean, native Feishu/Lark Doc. Preserve the source's facts, arguments, code, links, and media; improve only structure and presentation.

## Workflow

1. Read the complete Markdown source and resolve image paths relative to that file.
2. Read [references/design-system.md](references/design-system.md) before making layout decisions.
3. Read [references/lark-xml-contract.md](references/lark-xml-contract.md) before writing the Feishu XML payload.
4. Create one XML payload using the source content and the Minimal Editorial rules. Do not add search keywords, SEO sections, invented facts, or unsupported claims.
5. Validate it:

   ```bash
   python3 scripts/validate_payload.py ./payload.xml --base-dir ./source-directory
   ```

6. Unless the user explicitly asked for a dry run, publish immediately:

   ```bash
   python3 scripts/publish_payload.py ./payload.xml --base-dir ./source-directory
   ```

   Add exactly one destination option only when supplied: `--folder-token`, `--wiki-node`, or `--wiki-space`.
7. Return the document URL, title, and concise publication summary. Do not claim success without a URL.

## Content invariants

- Keep every source fact and the original argument order unless moving a heading is necessary to repair hierarchy.
- Never remove code, links, tables, images, warnings, or action items merely to reduce length.
- A long document may receive a three-bullet “速览”/“At a glance” callout only when no equivalent summary exists. Every bullet must be entailed by the source.
- Use semantic native blocks rather than decorative glyphs or simulated boxes.
- Treat GEO/SEO as repository-discoverability work, not as generated-document content.

## Publishing and setup

The publisher intentionally delegates authentication and API compatibility to the official `lark-cli`. If it is missing, unauthenticated, or lacks scopes, read [references/publishing.md](references/publishing.md). Installation and login require user participation; do not silently install software or switch identities.

Use `--dry-run` only for explicit preview, testing, or troubleshooting. Normal invocations publish directly as the authenticated user.
