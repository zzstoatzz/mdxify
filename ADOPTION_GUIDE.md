# Using mdxify

## Quick Start

### Run without installing (using uvx)
```bash
uvx mdxify --help
```

### Basic Commands

**Generate docs for your package:**
```bash
mdxify --all --root-module mypackage
```

**Generate docs for specific modules only:**
```bash
mdxify mypackage.core mypackage.api mypackage.models
```

**Change output directory:**
```bash
mdxify --all --root-module mypackage --output-dir docs/python-sdk
```
(Default is `docs/python-sdk`)

**Skip navigation file updates:**
```bash
mdxify --all --root-module mypackage --no-update-nav
```

## What It Does

1. Reads your Python files using AST (doesn't import them)
2. Extracts classes, functions, methods, and their docstrings
3. Generates `.mdx` files with formatted documentation
4. Optionally updates a `docs.json` navigation file

## Output

For a module like `mypackage.core.auth`, you get:
- File: `docs/python-sdk/mypackage-core-auth.mdx`
- Contains: All public classes, functions, methods with their signatures and docstrings
- Formatted: MDX with proper escaping for type annotations

That's it. Run it, get MDX files.

## Navigation Updates

If your documentation framework uses a `docs.json` file (like Mintlify), mdxify can automatically update your navigation. Add this placeholder where you want the API docs to appear:

```json
{
  "navigation": {
    "anchors": [
      {
        "anchor": "API Reference",
        "groups": [
          {
            "group": "Python API",
            "pages": [
              "api/overview",
              {"$mdxify": "generated"},
              "api/advanced"
            ]
          }
        ]
      }
    ]
  }
}
```

mdxify will replace `{"$mdxify": "generated"}` with your module structure. Without this placeholder, you'll see a warning and need to manually add the generated files to your navigation.

## GitHub Actions Example

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

## Example Output Structure

For a package like:
```
mypackage/
├── __init__.py
├── core.py
├── utils/
│   ├── __init__.py
│   ├── helpers.py
│   └── validators.py
└── models/
    ├── __init__.py
    └── base.py
```

You get:
```
docs/python-sdk/
├── mypackage-__init__.mdx
├── mypackage-core.mdx
├── mypackage-utils-__init__.mdx
├── mypackage-utils-helpers.mdx
├── mypackage-utils-validators.mdx
├── mypackage-models-__init__.mdx
└── mypackage-models-base.mdx
```