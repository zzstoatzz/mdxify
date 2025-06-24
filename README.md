# mdxify

Generate MDX API documentation from Python modules with automatic navigation structure.

## Installation

```bash
pip install mdxify
```

## Usage

Generate documentation for all modules in a package:

```bash
mdxify --all --root-module mypackage --output-dir docs/python-sdk
```

Generate documentation for specific modules:

```bash
mdxify mypackage.core mypackage.utils --output-dir docs/python-sdk
```

Exclude internal modules from documentation:

```bash
mdxify --all --root-module mypackage --exclude mypackage.internal --exclude mypackage.tests
```

### Options

- `modules`: Specific modules to document
- `--all`: Generate documentation for all modules under the root module
- `--root-module`: Root module to generate docs for (required when using --all)
- `--output-dir`: Output directory for generated MDX files (default: docs/python-sdk)
- `--update-nav/--no-update-nav`: Update docs.json navigation (default: True)
- `--skip-empty-parents`: Skip parent modules that only contain boilerplate (default: False)
- `--anchor-name` / `--navigation-key`: Name of the navigation anchor or group to update (default: 'SDK Reference')
- `--exclude`: Module to exclude from documentation (can be specified multiple times). Excludes the module and all its submodules.
- `--repo-url`: GitHub repository URL for source code links (e.g., https://github.com/owner/repo). If not provided, will attempt to detect from git remote.
- `--branch`: Git branch name for source code links (default: main)

### Navigation Updates

mdxify can automatically update your `docs.json` navigation by finding either anchors or groups:

1. **First run**: Add a placeholder in your `docs.json` using either format:

**Anchor format (e.g., FastMCP):**
```json
{
  "navigation": [
    {
      "anchor": "SDK Reference",
      "pages": [
        {"$mdxify": "generated"}
      ]
    }
  ]
}
```

**Group format (e.g., Prefect):**
```json
{
  "navigation": [
    {
      "group": "SDK Reference",
      "pages": [
        {"$mdxify": "generated"}
      ]
    }
  ]
}
```

2. **Subsequent runs**: mdxify will find and update the existing anchor or group directly - no placeholder needed!

The `--anchor-name` parameter (or its alias `--navigation-key`) identifies which anchor or group to update.

### Source Code Links

mdxify can automatically add links to source code on GitHub for all functions, classes, and methods:

```bash
# Auto-detect repository from git remote
mdxify --all --root-module mypackage

# Or specify repository explicitly
mdxify --all --root-module mypackage --repo-url https://github.com/owner/repo --branch develop
```

This adds source links next to each function/class/method that link directly to the code on GitHub.

#### Customizing Source Link Text

You can customize the link text/symbol using the `MDXIFY_SOURCE_LINK_TEXT` environment variable:

```bash
# Use custom text
export MDXIFY_SOURCE_LINK_TEXT="[src]"
mdxify --all --root-module mypackage

# Use emoji
export MDXIFY_SOURCE_LINK_TEXT="🔗"
mdxify --all --root-module mypackage

# Use different Unicode symbol (default is "view on GitHub ↗")
export MDXIFY_SOURCE_LINK_TEXT="⧉"
mdxify --all --root-module mypackage
```

## Features

- **Fast AST-based parsing** - No module imports required
- **MDX output** - Compatible with modern documentation frameworks
- **Automatic navigation** - Generates hierarchical navigation structure
- **Google-style docstrings** - Formats docstrings using Griffe
- **Smart filtering** - Excludes private modules and known test patterns

## Development

```bash
# Install development dependencies
uv sync

# Run tests
uv run pytest

# Run type checking
uv run ty check

# Run linting
uv run ruff check src/ tests/
```