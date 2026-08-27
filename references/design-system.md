# Minimal Editorial design system

Read this file whenever converting Markdown into a Feishu document. The goal is a document that feels edited, not decorated.

## Hierarchy

- Use the Feishu page title for the document title. Do not repeat it as the first body heading.
- Prefer `h2` for major sections and `h3` for subsections. Use `h4` only when the source genuinely needs a third body level.
- Repair skipped heading levels without changing the source's argument order.
- Keep paragraphs focused. Split a paragraph only when it contains clearly independent ideas; do not paraphrase merely to make it shorter.
- Retain lists when the source expresses steps, choices, requirements, or parallel items. Do not turn ordinary prose into a wall of bullets.

## Emphasis and color

Color communicates meaning; it is not decoration.

| Meaning | Native treatment |
| --- | --- |
| Context or useful information | `light-blue` callout, `💡` or `📌` |
| Caution or dependency | `light-yellow` callout, `⚠️` |
| Decision, conclusion, or completed outcome | `light-green` callout, `✅` |
| Confirmed error or critical risk | `light-red` callout, `❗` |

- Keep the default text color for ordinary prose.
- Highlight only a keyword or short phrase with `<span background-color="light-yellow">…</span>` or another semantic light color.
- Never highlight a full paragraph. Keep highlighted characters below roughly 8% of body text.
- Use at most three callouts in an ordinary document and at most one per major section.
- Avoid colored headings, decorative borders, gradients, and simulated UI cards.

## Components

- Tables: use `light-gray` or `medium-gray` headers. Add colored cells only for real status/category encoding.
- Code: preserve the language and content exactly; add a caption only when the source supplies a meaningful label.
- Images: preserve order, alt text as caption, and source path/URL. Do not invent captions.
- Mermaid: convert to a native editable whiteboard. Preserve the Mermaid source, including style directives.
- Dividers: reserve for major transitions; headings already provide separation.
- Emoji: use sparingly in callout icons or source text. Do not prefix every heading.
- Columns: avoid by default; long-form Feishu documents should remain readable on narrow screens.

Choose components by information role, not by decoration:

| Source role | Preferred native treatment |
| --- | --- |
| Executive conclusion or weekly summary | One opening information Callout |
| KPI table with explicit status | Gray header plus color only in status cells |
| Explicitly completed work | Checked `checkbox` blocks |
| Simple Mermaid process or architecture | Editable `whiteboard` |
| Risk or unresolved dependency | Caution Callout |
| Recorded decision or governing rule | `blockquote` |
| Ordered next steps | `ol` |

Do not invent a status, completion state, diagram, or decision to justify a component. If the source does not carry that meaning, keep ordinary prose or lists.

## At-a-glance summary

For a document longer than about 1,200 CJK characters or 800 English words, add one opening callout only if no summary already exists:

```xml
<callout emoji="📌" background-color="light-blue">
  <p><b>速览</b></p>
  <ul>
    <li>最多三条，只陈述原文明确支持的要点。</li>
  </ul>
</callout>
```

Do not add this block to short documents. Do not use it for SEO or introduce new claims.

## Final editorial check

- Facts, numbers, code, URLs, warnings, and action items are all retained.
- The first screen reveals the purpose without a decorative cover page.
- A reader can scan headings and callouts without reading repeated content.
- Removing a color would remove meaning; otherwise remove the color.
