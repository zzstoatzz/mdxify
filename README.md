# mdxify

Generate API documentation from Python modules with automatic navigation and source links. MDX is the default output today; Markdown support is planned.

## Projects Using mdxify

mdxify powers the API docs for:

- [FastMCP](https://github.com/jlowin/fastmcp) — live at https://gofastmcp.com/python-sdk
- [Prefect](https://github.com/PrefectHQ/prefect) — API ref at https://docs.prefect.io/v3/api-ref/python

## Installation

```bash
pip install mdxify
```

## Quick Start

<details>
<summary>Basic commands</summary>

Generate docs for all modules in a package:

```bash
mdxify --all --root-module mypackage --output-dir docs/python-sdk
```

Generate docs for specific modules:

```bash
mdxify mypackage.core mypackage.utils --output-dir docs/python-sdk
```

Exclude internal modules:

```bash
mdxify --all --root-module mypackage \
  --exclude mypackage.internal --exclude mypackage.tests
```

</details>

<details>
<summary>GitHub Actions example</summary>

Create `.github/workflows/docs.yml`:

```yaml
name: Generate API Docs

on:
  push:
    branches: [main]
    paths:
      - 'src/**/*.py'
      - 'pyproject.toml'

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Generate API documentation
        run: uvx mdxify --all --root-module mypackage --output-dir docs/python-sdk
      - name: Commit changes
        uses: stefanzweifel/git-auto-commit-action@v4
        with:
          commit_message: 'docs: update API reference [skip ci]'
          file_pattern: 'docs/python-sdk/**/*.mdx'
```

</details>

## CLI Options

- `modules`: Modules to document
- `--all`: Generate docs for all modules under the root module
- `--root-module`: Root module (required with `--all`)
- `--output-dir`: Output directory (default: `docs/python-sdk`)
- `--update-nav/--no-update-nav`: Update Mintlify `docs.json` (default: True)
- `--skip-empty-parents`: Skip boilerplate parents in nav (default: False)
- `--anchor-name` / `--navigation-key`: Anchor/group name to update (default: `SDK Reference`)
- `--exclude`: Module(s) to exclude (repeatable, excludes submodules too)
- `--repo-url`: GitHub repo for source links (auto-detected if omitted)
- `--branch`: Git branch for source links (default: `main`)

## Navigation Updates (Mintlify)

mdxify can update `docs/docs.json` by finding either anchors or groups. Add a placeholder for the first run:

Anchor format:

```json
{
  "navigation": [
    { "anchor": "SDK Reference", "pages": [{ "$mdxify": "generated" }] }
  ]
}
```

Group format:

```json
{
  "navigation": [
    { "group": "SDK Reference", "pages": [{ "$mdxify": "generated" }] }
  ]
}
```

Subsequent runs will update the existing anchor/group automatically. Configure the target with `--anchor-name` (alias `--navigation-key`).

## Source Code Links

Add GitHub source links to functions/classes/methods:

```bash
# Auto-detect repository from git remote
mdxify --all --root-module mypackage

# Or specify repository explicitly
mdxify --all --root-module mypackage \
  --repo-url https://github.com/owner/repo --branch develop
```

Customize link text via `MDXIFY_SOURCE_LINK_TEXT` if desired.

## Features

- Fast AST-based parsing (no imports)
- MDX output with safe escaping
- Automatic hierarchical navigation (Mintlify)
- Google-style docstrings via Griffe
- Smart filtering of private modules

## Development

See `CONTRIBUTING.md` for local setup, testing, linting, and release guidance.
