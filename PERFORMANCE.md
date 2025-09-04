# Performance Guide

This guide provides recommendations for optimal mdxify performance in CI/CD and pre-commit scenarios.

## Quick Start: Fastest Invocation

### 1. Use the Python API (Recommended for CI/CD)

For best performance in automated workflows, use the programmatic API:

```python
# scripts/generate_api_ref.py
from mdxify import generate_docs

result = generate_docs(
    "prefect",
    output_dir="docs/v3/api-ref/python",
    exclude=["prefect.agent"],
    anchor_name="Python SDK Reference",
    include_inheritance=True,
    repo_url="https://github.com/PrefectHQ/prefect",
)

print(f"✓ Generated {result['modules_processed']} modules in {result['time_elapsed']:.3f}s")
if result['modules_failed']:
    print(f"✗ Failed: {result['modules_failed']} modules")
```

This avoids all CLI startup overhead and is the fastest option.

### 2. Use `uv run` for CLI (Good Performance)

If you need the CLI, use `uv run` directly:

```bash
uv run mdxify \
  --all \
  --root-module prefect \
  --output-dir docs/v3/api-ref/python \
  --exclude prefect.agent
```

### 3. Use `uvx` Without --refresh-package (Acceptable Performance)

For one-off runs with uvx:

```bash
uvx mdxify \
  --all \
  --root-module prefect \
  --output-dir docs/v3/api-ref/python
```

**Note:** Avoid `--refresh-package` unless necessary. It adds ~2s overhead.

## Performance Comparison

Based on benchmarking with Prefect (290 modules):

| Method | Time | Notes |
|--------|------|-------|
| Python API | ~0.6-1.0s | Core generation only, no overhead |
| `uv run` | ~0.7-1.5s | Minimal CLI overhead |
| `uvx` (no refresh) | ~1.0-2.0s | Some environment resolution |
| `uvx --refresh-package` | ~3.0-5.0s | Full package refresh |

## Pre-commit Hook Example

For pre-commit/pre-push hooks, use the Python API:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: generate-api-docs
        name: Generate API Documentation
        entry: python scripts/generate_api_ref.py
        language: python
        additional_dependencies: [mdxify]
        pass_filenames: false
        stages: [push]
```

## Tips for Large Codebases

1. **Use parallel processing**: mdxify automatically uses 8 workers for parallel processing
2. **Exclude unnecessary modules**: Use `--exclude` to skip internal/test modules
3. **Consider incremental updates**: For development, generate only changed modules
4. **Pin mdxify version**: Avoid version resolution overhead by pinning: `mdxify==0.x.x`

## Troubleshooting Slow Performance

If mdxify seems slow:

1. **Check for --refresh-package**: Remove it if not needed
2. **Verify Python environment**: Ensure mdxify is installed in the active environment
3. **Profile imports**: Heavy user code imports can slow down parsing
4. **Use verbose mode**: Add `-v` to see per-module timing

## Future Improvements

We're working on:
- Incremental generation (only rebuild changed modules)
- Caching of parsed module data
- Further lazy loading optimizations