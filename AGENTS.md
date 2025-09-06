# AGENTS.md

Agent notes for working in this repository. The scope of this file is the entire repo.

## Working Directory & Module Discovery

- Always confirm `pwd` before running commands.
- When testing mdxify on other projects, ensure modules are importable from CWD or run from the target project with:
  - `uv run --with-editable /path/to/mdxify mdxify`
- Prefer `uv run -m` over invoking Python directly.

## UV Usage

- Use `uv run` for scripts and tests.
- Use `uvx mdxify@version` to test a specific PyPI version.

## Testing Discipline

- Run the full test suite: `uv run pytest -xvs`.
- For navigation/output changes, validate against a real project (e.g., FastMCP).

## Git & Releases

- Run pre-commit before pushing: `uv run pre-commit run --all-files`.
- Push to `main` before creating a release.
- Create releases with `gh release create` (CI handles PyPI).

## Focus

- Don’t fixate on arbitrary details; align with user requirements.
- Ask for clarification when intent isn’t clear.

