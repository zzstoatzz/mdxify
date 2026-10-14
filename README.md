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
- Properties documented as attributes, with read/write access labels
- Explicit static/class-method labels and caller-facing class-method signatures

### Class Members

Properties appear once under **Properties**, before **Methods**, using the
getter's return annotation rather than a callable signature. For example:

````markdown
**Properties:**

#### `name`

```python
name: str
```

*Read/write.*
````

A property without a setter is labeled read-only; a deleter adds a deletable
label. Getter documentation and any setter/deleter documentation stay together
in the property entry. Without a getter annotation, only the property name is
shown. Class-docstring **Attributes** descriptions remain available separately.

Static and class methods stay under **Methods** with explicit kind labels.
Class-method signatures omit the implicit receiver (`cls`); static-method
arguments and instance-method signatures retain their parameters. These member
presentations work in both MDX and Markdown, including directly inherited
members when `--include-inheritance` is enabled.

Decorator recognition supports the conventional `@property`, `@staticmethod`,
and `@classmethod` names (also qualified with `builtins`), and same-name local
property accessors such as `@name.setter`. It does not resolve decorator aliases,
custom descriptors, cached properties, or accessor extensions such as
`@Base.name.setter`.

## Development

See `CONTRIBUTING.md` for local setup, testing, linting, and release guidance.


> [!IMPORTANT]
> This project is not associated with the company Mintlify.
