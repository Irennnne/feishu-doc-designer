# Feishu/Lark XML contract

The official `lark-cli docs +create` XML format maps a compact HTML-like fragment to native document blocks. This skill emits XML because native callouts, highlights, editable whiteboards, and richer tables are not fully expressible in plain Markdown.

Canonical upstream references:

- [Official lark-doc skill](https://github.com/larksuite/cli/blob/main/skills/lark-doc/SKILL.md)
- [Official XML syntax reference](https://github.com/larksuite/cli/blob/main/skills/lark-doc/references/lark-doc-xml.md)
- [Official create shortcut reference](https://github.com/larksuite/cli/blob/main/skills/lark-doc/references/lark-doc-create.md)

Use the locally installed `lark-cli docs --help` as the runtime source of truth when flags differ from this file.

## Document skeleton

The payload is an XML fragment, not a single wrapper element. It begins with exactly one title:

```xml
<title>Project plan</title>
<h2>Goal</h2>
<p>Ship the validated pilot.</p>
```

Supported by this skill's validator:

- Blocks: `title`, `p`, `h1`–`h9`, `blockquote`, `hr`, `ul`, `ol`, `li`, `checkbox`, `pre`, `code`, `img`, `source`, `figure`, `table`, `thead`, `tbody`, `tfoot`, `tr`, `th`, `td`, `colgroup`, `col`, `callout`, `grid`, `column`, `whiteboard`.
- Inline: `b`, `em`, `u`, `del`, `br`, `span`, `a`, `latex`.

Prefer only the smaller subset required by the source.

## Mapping rules

### Inline text

```xml
<p>Use <b>bold</b>, <em>emphasis</em>, <u>underline</u>, <del>deleted</del>,
<span background-color="light-yellow">short highlights</span>, and
<a href="https://example.com">links</a>.</p>
```

Escape text content only: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`. Do not escape the XML tags.

### Lists and tasks

```xml
<ol>
  <li>First step<ul><li>Nested detail</li></ul></li>
  <li>Second step</li>
</ol>
<checkbox done="false">Follow up</checkbox>
```

Keep a nested list inside its parent `li`.

### Code

```xml
<pre lang="python" caption="Optional source caption"><code>print(&quot;hello&quot;)</code></pre>
```

The `code` element is mandatory inside `pre`. Preserve whitespace and escape XML-sensitive characters.

### Tables

```xml
<table>
  <thead><tr>
    <th background-color="light-gray"><p>Item</p></th>
    <th background-color="light-gray"><p>Status</p></th>
  </tr></thead>
  <tbody><tr><td><p>Pilot</p></td><td><p>Ready</p></td></tr></tbody>
</table>
```

Use `colspan`, `rowspan`, and `vertical-align` only when the Markdown source requires them.

### Callouts

```xml
<callout emoji="⚠️" background-color="light-yellow" border-color="yellow">
  <p><b>Dependency</b>: production access is still pending.</p>
</callout>
```

Callouts may contain paragraphs, lists, and checkboxes. They may not contain tables, images, code blocks, dividers, grids, whiteboards, resources, or nested callouts.

### Images and attachments

```xml
<img path="@./images/local.png" caption="Caption from Markdown alt text"/>
<img href="https://example.com/image.webp" caption="Remote image"/>
<source path="@./files/report.pdf" name="report.pdf"/>
```

Local paths must use `@./` and resolve inside the supplied `--base-dir`. The publisher copies them to an isolated staging directory before upload. Supported images are PNG, JPEG, GIF, and WebP up to 20 MiB.

### Mermaid

Use an editable whiteboard rather than a screenshot or ordinary code block:

```xml
<whiteboard type="mermaid">graph TD
  A[Markdown] --&gt; B[Feishu XML]
  B --&gt; C[Native Doc]
</whiteboard>
```

Preserve Mermaid `style` and `classDef` directives. XML-escape `<`, `>`, and `&` inside the diagram source.

## Unsupported input

- Raw HTML/CSS intended for a browser cannot be reproduced in native Feishu Docs.
- JavaScript, animations, arbitrary fonts, gradients, and fixed-position layouts are out of scope.
- Existing-document replacement/synchronization is out of scope for v1.
