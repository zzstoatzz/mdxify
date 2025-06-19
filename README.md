# mdxify

Generate MDX API documentation from Python modules with automatic navigation structure.

## Installation

```bash
pip install mdxify
```

## Usage

Generate documentation for all modules in a package:

```bash
mdxify --all --root-module mypackage --output-dir docs/api
```

Generate documentation for specific modules:

```bash
mdxify mypackage.core mypackage.utils --output-dir docs/api
```

### Options

- `modules`: Specific modules to document (if none specified, generates all)
- `--all`: Generate documentation for all modules under the root module
- `--root-module`: Root module to generate docs for (default: prefect)
- `--output-dir`: Output directory for generated MDX files (default: docs/v3/api-ref)
- `--update-nav/--no-update-nav`: Update docs.json navigation (default: True)

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