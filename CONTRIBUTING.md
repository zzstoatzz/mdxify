# Contributing to mdxify

Thanks for contributing! This guide outlines local development, testing, and release tips.

## Local Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest -xvs

# Type checking
uv run ty check

# Linting
uv run ruff check src/ tests/

# Pre-commit hooks
uv run pre-commit install
uv run pre-commit run --all-files
```

## Working Practices

- Prefer small, focused PRs with clear titles and descriptions.
- For navigation/output changes, test on a real project (e.g., FastMCP) where possible.
- Ask for clarification if goals are ambiguous.

## Releasing

- Ensure tests pass and pre-commit is clean.
- Push to `main` before creating a release.
- Use `gh release create` (GitHub Actions handles PyPI publishing).

## Notes on Navigation Structure

- Top-level groups use fully-qualified names (e.g., `fastmcp.client`).
- Nested groups use simple names (e.g., `auth`).
- Entries are sorted: plain pages first, then groups alphabetically.

## Default Paths

- Default output directory: `docs/python-sdk`
- Default navigation anchor: `SDK Reference`

