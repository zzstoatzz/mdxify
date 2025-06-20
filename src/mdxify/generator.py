"""MDX documentation generation."""

from pathlib import Path
from typing import Any

from .formatter import escape_mdx_content, format_docstring_with_griffe


def is_module_empty(module_path: Path) -> bool:
    """Check if a module documentation file indicates it's empty."""
    if not module_path.exists():
        return True

    content = module_path.read_text()
    return (
        "*This module is empty or contains only private/internal implementations.*"
        in content
    )


def generate_mdx(module_info: dict[str, Any], output_file: Path) -> None:
    """Generate MDX documentation from module info."""
    lines = []

    # Frontmatter
    lines.append("---")
    # If this is an __init__ file, use __init__ as the title
    if output_file.stem.endswith("-__init__"):
        lines.append("title: __init__")
        lines.append("sidebarTitle: __init__")
    else:
        module_name = module_info["name"].split(".")[-1]
        lines.append(f"title: {module_name}")
        lines.append(f"sidebarTitle: {module_name}")
    lines.append("---")
    lines.append("")

    # Module header
    lines.append(f"# `{module_info['name']}`")
    lines.append("")

    # Check if module is effectively empty
    has_content = (
        module_info.get("docstring")
        or module_info.get("functions")
        or module_info.get("classes")
    )

    if not has_content:
        lines.append(
            "*This module is empty or contains only private/internal implementations.*"
        )
        lines.append("")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(lines))
        return

    if module_info["docstring"]:
        lines.append("")
        lines.append(escape_mdx_content(module_info["docstring"]))
        lines.append("")

    # Functions
    if module_info["functions"]:
        lines.append("## Functions")
        lines.append("")

        for func in module_info["functions"]:
            lines.append(f"### `{func['name']}`")
            lines.append("")
            lines.append("```python")
            lines.append(func["signature"])
            lines.append("```")
            lines.append("")

            if func["docstring"]:
                lines.append("")
                # Format docstring with Griffe
                formatted_docstring = format_docstring_with_griffe(func["docstring"])
                lines.append(escape_mdx_content(formatted_docstring))
                lines.append("")

    # Classes
    if module_info["classes"]:
        lines.append("## Classes")
        lines.append("")

        for cls in module_info["classes"]:
            lines.append(f"### `{cls['name']}`")
            lines.append("")

            if cls["docstring"]:
                lines.append("")
                # Format docstring with Griffe
                formatted_docstring = format_docstring_with_griffe(cls["docstring"])
                lines.append(escape_mdx_content(formatted_docstring))
                lines.append("")

            if cls["methods"]:
                lines.append("**Methods:**")
                lines.append("")

                for method in cls["methods"]:
                    lines.append(f"#### `{method['name']}`")
                    lines.append("")
                    lines.append("```python")
                    lines.append(method["signature"])
                    lines.append("```")
                    lines.append("")

                    if method["docstring"]:
                        formatted_docstring = format_docstring_with_griffe(
                            method["docstring"]
                        )
                        lines.append(escape_mdx_content(formatted_docstring))
                        lines.append("")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines))