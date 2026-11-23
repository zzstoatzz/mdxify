# AGENTS.md

## testing

- To run mdxify against another project, run it from that project so its
  modules import: `uv run --with-editable /path/to/mdxify mdxify`.
- Use `uvx mdxify@version` to test a specific PyPI version.
- Run the full test suite: `uv run pytest -xvs`.
- For navigation/output changes, validate against a real project (e.g., FastMCP).

## git and releases

- Run pre-commit before pushing: `uv run pre-commit run --all-files`.
- Push to `main` before creating a release.
- Create releases with `gh release create` (CI handles PyPI).
