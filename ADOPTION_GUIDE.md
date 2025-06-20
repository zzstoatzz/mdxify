# Using mdxify

## Quick Start

### Run without installing (using uvx)
```bash
uvx mdxify --help
```

### Basic Commands

**Generate docs for everything in a package:**
```bash
mdxify --all
```
(Defaults to looking for a package called `prefect`)

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
mdxify --all --output-dir docs/api
```
(Default is `docs/v3/api-ref`)

**Skip navigation file updates:**
```bash
mdxify --all --no-update-nav
```

## What It Does

1. Reads your Python files using AST (doesn't import them)
2. Extracts classes, functions, methods, and their docstrings
3. Generates `.mdx` files with formatted documentation
4. Optionally updates a `docs.json` navigation file

## Output

For a module like `mypackage.core.auth`, you get:
- File: `docs/api/mypackage-core-auth.mdx`
- Contains: All public classes, functions, methods with their signatures and docstrings
- Formatted: MDX with proper escaping for type annotations

That's it. Run it, get MDX files.

## Integration Examples

### Mintlify Setup

1. Install mdxify as a dev dependency:
```bash
uv add --dev mdxify
```

2. Add to your `package.json` scripts:
```json
{
  "scripts": {
    "generate-api-docs": "mdxify --all --root-module mypackage --output-dir docs/api-reference"
  }
}
```

3. Update your `mint.json` navigation:
```json
{
  "navigation": [
    {
      "group": "API Reference",
      "pages": [
        "api-reference/introduction",
        {
          "group": "mypackage",
          "pages": ["api-reference/mypackage-*"]
        }
      ]
    }
  ]
}
```

### GitHub Actions CI/CD

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
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install mdxify
          pip install -e .  # Install your package
      
      - name: Generate API documentation
        run: mdxify --all --root-module mypackage --output-dir docs/api
      
      - name: Commit changes
        uses: stefanzweifel/git-auto-commit-action@v4
        with:
          commit_message: 'docs: update API reference [skip ci]'
          file_pattern: 'docs/api/**/*.mdx'
```

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: generate-api-docs
        name: Generate API docs
        entry: mdxify --all --root-module mypackage --output-dir docs/api
        language: system
        pass_filenames: false
        always_run: true
```

## Configuration

### Custom Module Filtering

Create a wrapper script `generate_docs.py`:

```python
#!/usr/bin/env python
import subprocess
import sys

# Define modules to exclude
EXCLUDE_MODULES = [
    "mypackage.internal",
    "mypackage.experimental",
    "mypackage.tests",
]

def should_document_module(module_name):
    """Custom logic for module filtering."""
    for excluded in EXCLUDE_MODULES:
        if module_name.startswith(excluded):
            return False
    return True

def main():
    # Get all modules
    result = subprocess.run(
        ["python", "-c", "import mypackage; print(mypackage.__path__)"],
        capture_output=True,
        text=True
    )
    
    # Filter and generate docs only for public modules
    modules_to_document = []
    # ... custom logic to find modules ...
    
    subprocess.run([
        "mdxify",
        *modules_to_document,
        "--output-dir", "docs/api"
    ])

if __name__ == "__main__":
    main()
```

### Docstring Best Practices

mdxify works best with Google-style docstrings:

```python
def process_data(
    input_file: Path,
    output_format: str = "json",
    validate: bool = True
) -> dict[str, Any]:
    """Process data from input file and return structured output.
    
    This function reads data from the input file, validates it if requested,
    and returns the processed data in the specified format.
    
    Args:
        input_file: Path to the input data file
        output_format: Desired output format. Options: "json", "yaml", "csv"
        validate: Whether to validate data before processing
        
    Returns:
        Dictionary containing processed data with keys:
        - "data": The processed data
        - "metadata": Processing metadata
        - "errors": List of any errors encountered
        
    Raises:
        FileNotFoundError: If input_file doesn't exist
        ValueError: If output_format is not supported
        ValidationError: If validate=True and data is invalid
        
    Examples:
        Basic usage:
        
        ```python
        result = process_data(Path("data.csv"))
        print(result["data"])
        ```
        
        With validation:
        
        ```python
        result = process_data(
            Path("data.csv"),
            output_format="yaml",
            validate=True
        )
        ```
    """
```

## Advanced Usage

### Incremental Documentation

Only regenerate docs for changed modules:

```bash
# Find changed Python files
CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD | grep '\.py$')

# Extract module names and generate docs
for file in $CHANGED_FILES; do
    MODULE=$(echo $file | sed 's/src\///' | sed 's/\.py$//' | tr '/' '.')
    mdxify $MODULE --output-dir docs/api
done
```

### Custom MDX Components

Post-process generated MDX to add custom components:

```python
from pathlib import Path
import re

def add_custom_components(mdx_file: Path):
    """Add custom MDX components to generated files."""
    content = mdx_file.read_text()
    
    # Add custom import at the top
    content = "import { APIBadge } from '@/components/APIBadge'\n\n" + content
    
    # Add badges to class definitions
    content = re.sub(
        r'### `(class \w+)`',
        r'### `\1` <APIBadge type="class" />',
        content
    )
    
    mdx_file.write_text(content)

# Process all generated MDX files
for mdx_file in Path("docs/api").glob("**/*.mdx"):
    add_custom_components(mdx_file)
```

### Navigation Structure

mdxify generates a hierarchical navigation structure. For a package like:

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

The generated structure will be:

```
docs/api/
├── mypackage-__init__.mdx
├── mypackage-core.mdx
├── mypackage-utils-__init__.mdx
├── mypackage-utils-helpers.mdx
├── mypackage-utils-validators.mdx
├── mypackage-models-__init__.mdx
└── mypackage-models-base.mdx
```

With navigation JSON:

```json
[
  {
    "group": "utils",
    "pages": [
      "v3/api-ref/mypackage-utils-__init__",
      "v3/api-ref/mypackage-utils-helpers",
      "v3/api-ref/mypackage-utils-validators"
    ]
  },
  {
    "group": "models",
    "pages": [
      "v3/api-ref/mypackage-models-__init__",
      "v3/api-ref/mypackage-models-base"
    ]
  },
  "v3/api-ref/mypackage-core"
]
```

## Troubleshooting

### Common Issues

1. **Import errors when running mdxify**
   - Solution: mdxify uses AST parsing, so your package doesn't need to be importable
   - If you see import errors, they're likely from your code trying to import missing dependencies

2. **Empty documentation files**
   - Check if your modules have public classes/functions (not starting with `_`)
   - Ensure docstrings are present
   - Verify the module isn't in the exclusion list

3. **MDX parsing errors**
   - mdxify automatically escapes problematic characters
   - If issues persist, check for unclosed code blocks in docstrings

4. **Navigation not updating**
   - Ensure `docs.json` exists and has the expected structure
   - Use `--no-update-nav` if managing navigation manually

### Debug Mode

Run with verbose output:

```bash
# See which modules are being processed/skipped
mdxify --all --root-module mypackage --output-dir docs/api 2>&1 | tee mdxify.log
```

## Integration Checklist

- [ ] Install mdxify as a dev dependency
- [ ] Run mdxify locally to test output
- [ ] Add generated docs directory to `.gitignore` (if generating dynamically)
- [ ] Set up CI/CD pipeline for automatic updates
- [ ] Configure your documentation framework to read the MDX files
- [ ] Add custom styling/components as needed
- [ ] Document any project-specific conventions

## Contributing to mdxify

Found a bug or want a feature? Visit: https://github.com/zzstoatzz/mdxify

## License

mdxify is MIT licensed. Your generated documentation maintains your project's license.