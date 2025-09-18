# generate api docs for mdxify itself
generate-docs:
    uvx mdxify --all --root-module mdxify --output-dir docs/python-sdk

serve-docs:
    cd docs && npx mint@latest dev

# clean and rebuild docs
rebuild:
    rm -rf docs
    just generate-docs

# run tests
test:
    uv run pytest tests/ -xvs

# format and lint
fmt:
    uv run ruff format src/ tests/
    uv run ruff check src/ tests/ --fix