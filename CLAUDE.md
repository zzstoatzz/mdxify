# Development Notes for Claude

## Common Pitfalls to Avoid

### Working Directory Management
- **Always verify your current directory** with `pwd` before running commands
- When testing mdxify on other projects, remember that Python needs to find the modules:
  - Either run from the target project's directory with `uv run --with-editable /path/to/mdxify mdxify`
  - Or ensure the target modules are importable from your current directory
- Don't assume you're in the right directory - check first

### UV Usage (It's 2025!)
- **Always use `uv run`** instead of calling Python directly
- For testing local changes: `uv run --with-editable .` 
- For testing specific versions: `uvx mdxify@version`
- Don't use `python -m` directly when uv is available

### Testing Before Releasing
- **Always test your changes** before cutting a release
- Run the full test suite: `uv run pytest -xvs`
- For navigation/output changes, test on a real project (like FastMCP)
- Don't push and release without verifying the changes work

### Focus on What Matters
- Don't get fixated on arbitrary implementation details (like "api-reference/" prefixes)
- Focus on the actual requirements the user stated
- Ask for clarification if the goal isn't clear rather than making assumptions

### Git and Releases
- Commit messages should be clear and describe what changed
- Always push to main before creating a release
- Use `gh release create` for releases - GitHub Actions handles PyPI publishing

## Project-Specific Notes

### Navigation Structure
- Top-level groups use fully qualified names (e.g., `fastmcp.client`)
- Nested groups use simple names (e.g., `auth` under `fastmcp.client`)
- Navigation entries are sorted: plain pages first, then groups, alphabetically

### Default Paths
- Default output directory is `docs/python-sdk` (not `docs/api`)
- Navigation anchor is "SDK Reference" (not "API Reference")