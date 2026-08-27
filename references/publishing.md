# Publishing and authentication

Read this file only when setup, authentication, scope, identity, or publication fails.

## One-time setup

Feishu Doc Designer delegates authentication and document API compatibility to the official [Lark/Feishu CLI](https://github.com/larksuite/cli).

Requirements:

- Node.js supported by the current `@larksuite/cli` release.
- Python 3.9 or newer for this skill's validator/publisher.

Official installation flow:

```bash
npx @larksuite/cli@latest install
lark-cli config init --new
lark-cli auth login --recommend
lark-cli auth status
```

The configuration and login commands open an authorization URL. Let the user complete that flow; never request an App Secret in chat or commit credentials to this repository.

## Identity and destination

The publisher always uses `--as user` so the created document is owned by the authenticated user. Do not silently fall back to bot identity.

The skill exposes three mutually exclusive destination labels and maps them to the current official CLI interface:

- `--folder-token TOKEN` — user-accessible Drive folder → `lark-cli --parent-token`.
- `--wiki-node TOKEN` — create below an existing Wiki node → `lark-cli --parent-token`.
- `--wiki-space ID` — create at a Wiki space position → `lark-cli --parent-position`.

Without a destination option, create in the user's default document location.

## Failure handling

- `lark-cli is not installed`: obtain authorization before installing Node.js or the CLI, then run the official setup.
- Authentication/token error: run `lark-cli auth status`; if needed, run `lark-cli auth login --recommend` once and retry once.
- Scope error: follow the scope guidance returned by `lark-cli`; do not switch to broader credentials speculatively.
- Permission error for a folder/wiki: keep `--as user`, confirm the authenticated user can create there, and do not retry another destination without instruction.
- Degradation warning, missing document ID, or missing URL: treat publication as failed even if `ok` is true.
- Rate limit or transient server error: retry at most once after the server-provided delay. Do not loop indefinitely.

## Safe file transport

The publisher writes the XML and copied assets to an isolated temporary directory, sets that directory as the CLI working directory, and passes `--content @./document.xml` with `shell=False`. This avoids command substitution, quoting loss, and the CLI's restriction against absolute `@file` paths.
