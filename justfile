# generate api docs for mdxify itself
docs:
    uvx mdxify --all --root-module mdxify --output-dir docs/python-sdk

# clean and rebuild docs
rebuild:
    rm -rf docs/python-sdk
    just docs

# run tests
test:
    uv run pytest tests/ -xvs

# format and lint
fmt:
    uv run ruff format src/ tests/
    uv run ruff check src/ tests/ --fix