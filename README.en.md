# Feishu Doc Designer

[中文](README.md) · A skill for polished Markdown-to-Feishu publishing

![Feishu Doc Designer turns plain Markdown into a restrained native Feishu document](assets/hero.svg)

Feishu Doc Designer turns a local Markdown file into a clean, restrained, collaborative Feishu/Lark Doc and publishes it in one step. Instead of performing a literal `.md` import, it uses native headings, callouts, highlights, tables, code blocks, images, and editable Mermaid whiteboards.

It is designed for people looking for **Markdown to Feishu**, **Markdown to Lark Docs**, **Feishu document formatting**, **Lark document beautification**, or a reusable AI Agent Skill for publishing documentation.

## What makes it different

| Literal Markdown import | Feishu Doc Designer |
| --- | --- |
| Basic headings and paragraphs | Repairs hierarchy without changing the argument |
| Uniform blockquotes | Uses restrained semantic callouts |
| Mermaid remains code | Creates an editable native whiteboard |
| Local image paths are fragile | Stages and uploads local media |
| Long content can break shell quoting | Publishes through safe relative `@file` input with `shell=False` |

The project borrows the design-system, visual demonstration, and progressive-disclosure ideas of [frontend-slides](https://github.com/zarazhangrui/frontend-slides), while producing native long-form Feishu documents rather than CSS-driven web slides.

## Real Feishu output

The page below was generated and published from the repository's [proposal example](examples/proposal.md). The phrase highlight, callout, gray table header, and document hierarchy are all native Feishu components.

![Polished Feishu document showing a short phrase highlight, a light-blue callout, and a gray table header](assets/feishu-proposal-example.jpg)

## Quick start

Install and authenticate the official [Lark/Feishu CLI](https://github.com/larksuite/cli). Node.js and Python 3.9+ are required.

```bash
npx @larksuite/cli@latest install
lark-cli config init --new
lark-cli auth login --recommend
lark-cli auth status
```

Install the skill with a compatible Skills CLI:

```bash
npx skills add Irennnne/feishu-doc-designer -y -g
```

Or clone the repository into your agent's personal skills directory. Then invoke:

```text
Use $feishu-doc-designer to publish ./document.md as a polished Feishu document.
```

Normal invocations publish immediately. The first invocation still requires the one-time official CLI authorization flow.

## Editorial contract

- Preserve facts, figures, code, links, images, risks, and action items.
- GEO/SEO is used only to make this open-source skill discoverable; it never injects search content into user documents.
- Prefer H2/H3 body hierarchy and use color only for information, caution, conclusions, and confirmed risks.
- Highlight keywords or short phrases, not whole paragraphs. Ordinary documents should use no more than three callouts.
- A long document without a summary may receive an at-a-glance callout of up to three source-grounded bullets.

See the full [Minimal Editorial design system](references/design-system.md).

## Supported content

- Headings, paragraphs, inline emphasis/highlight, and links
- Ordered/unordered lists, tasks, quotes, and dividers
- Tables, code blocks, local/remote images, and attachments
- Mermaid diagrams as native editable Feishu whiteboards
- Drive folder, Wiki node, or Wiki space destination
- XML structure, color, nesting, resource-path, and empty-document validation
- Safe one-step publication with structured JSON output

Version 0.1 creates new documents only; it does not overwrite or synchronize an existing Feishu document.

## Examples

- [Proposal](examples/proposal.md) → [expected Feishu XML](examples/expected/proposal.xml)
- [Technical guide](examples/guide.md) → [expected Feishu XML](examples/expected/guide.xml)
- [Weekly report](examples/weekly-report.md) → [expected Feishu XML](examples/expected/weekly-report.xml)

## Script interface

The skill invokes these automatically; they are also useful for diagnostics:

```bash
python3 scripts/validate_payload.py ./payload.xml --base-dir ./document-assets
python3 scripts/publish_payload.py ./payload.xml --base-dir ./document-assets --dry-run
python3 scripts/publish_payload.py ./payload.xml --base-dir ./document-assets
```

Choose at most one destination: `--folder-token`, `--wiki-node`, or `--wiki-space`. The publisher maps these labels to the current official `--parent-token` / `--parent-position` interface.

## Security and limitations

- The publisher uses an argument vector, `shell=False`, and an isolated temporary directory. It never executes shell snippets from Markdown.
- Local assets must remain within `--base-dir`. Images support PNG, JPEG, GIF, or WebP up to 20 MiB each.
- Browser CSS, custom fonts, animations, gradients, and fixed positioning are not available in native Feishu Docs.
- Never commit an App Secret, access token, authorization state, or user document.

## License

[MIT](LICENSE)
