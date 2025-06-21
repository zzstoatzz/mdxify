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
- `--anchor-name`: Name of the navigation anchor to update (default: 'SDK Reference')
- `--exclude`: Module to exclude from documentation (can be specified multiple times). Excludes the module and all its submodules.

### Navigation Updates

mdxify can automatically update your `docs.json` navigation in two ways:

1. **First run**: Add a placeholder in your `docs.json`:

```json
{
  "navigation": [
    {
      "anchor": "SDK Reference",
      "groups": [
        {
          "group": "Modules", 
          "pages": [
            {"$mdxify": "generated"}
          ]
        }
      ]
    }
  ]
}
```

2. **Subsequent runs**: mdxify will find and update the existing anchor directly - no placeholder needed!

The navigation structure uses the `--anchor-name` parameter (default: "SDK Reference") to identify which section to update.

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