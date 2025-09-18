# `mdxify`

Generate API documentation from Python modules with automatic navigation and source links.

## Projects Using `mdxify`

- **[`mdxify`](https://github.com/zzstoatzz/mdxify)** — This documentation at [mdxify.zzstoatzz.io](https://mdxify.zzstoatzz.io)
- **[FastMCP](https://github.com/jlowin/fastmcp)** — API docs at [gofastmcp.com/python-sdk](https://gofastmcp.com/python-sdk)
- **[Prefect](https://github.com/PrefectHQ/prefect)** — API reference at [docs.prefect.io/v3/api-ref/python](https://docs.prefect.io/v3/api-ref/python)

## Quick Start

```bash
uvx mdxify --all --root-module mypackage --output-dir docs/python-sdk
```

## Documentation

📚 **[View full documentation →](https://mdxify.zzstoatzz.io)**

- [Introduction](https://mdxify.zzstoatzz.io/introduction)
- [Quick Start Guide](https://mdxify.zzstoatzz.io/quickstart)
- [API Reference](https://mdxify.zzstoatzz.io/python-sdk/mdxify-cli)

## Features

- Fast AST-based parsing
- MDX output with safe escaping
- Automatic hierarchical navigation (Mintlify)
- Google-style docstrings via Griffe
- Smart filtering of private modules

## Development

See `CONTRIBUTING.md` for local setup, testing, linting, and release guidance.


> [!IMPORTANT]
> This project is not associated with the company Mintlify.