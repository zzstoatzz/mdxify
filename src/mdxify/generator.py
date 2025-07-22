"""MDX documentation generation."""

from pathlib import Path
from typing import Any, Optional

from .formatter import escape_mdx_content, format_docstring_with_griffe
from .source_links import add_source_link_to_header, generate_source_link


def is_module_empty(module_path: Path) -> bool:
    """Check if a module documentation file indicates it's empty."""
    if not module_path.exists():
        return True

    content = module_path.read_text()
    return (
        "*This module is empty or contains only private/internal implementations.*"
        in content
    )


def generate_mdx(
    module_info: dict[str, Any], 
    output_file: Path,
    repo_url: Optional[str] = None,
    branch: str = "main",
    root_module: Optional[str] = None,
) -> None:
    """Generate MDX documentation from module info.
    
    Args:
        module_info: Parsed module information
        output_file: Path to write the MDX file
        repo_url: GitHub repository URL for source links
        branch: Git branch name for source links
        root_module: Root module name for finding relative paths
    """
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
            # Generate source link if possible
            source_link = None
            if repo_url and "source_file" in module_info and "line" in func:
                source_link = generate_source_link(
                    repo_url,
                    branch,
                    Path(module_info["source_file"]),
                    func["line"],
                    root_module,
                )
            
            header = f"### `{func['name']}`"
            header_with_link = add_source_link_to_header(header, source_link)
            lines.append(header_with_link)
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
            # Generate source link if possible
            source_link = None
            if repo_url and "source_file" in module_info and "line" in cls:
                source_link = generate_source_link(
                    repo_url,
                    branch,
                    Path(module_info["source_file"]),
                    cls["line"],
                    root_module,
                )
            
            header = f"### `{cls['name']}`"
            header_with_link = add_source_link_to_header(header, source_link)
            lines.append(header_with_link)
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
                    # Generate source link if possible
                    method_source_link = None
                    if repo_url and "line" in method:
                        # For inherited methods, use the source file from the method itself
                        # For regular methods, use the module's source file
                        source_file = method.get("source_file", module_info.get("source_file"))
                        if source_file:
                            method_source_link = generate_source_link(
                                repo_url,
                                branch,
                                Path(source_file),
                                method["line"],
                                root_module,
                            )
                    
                    # Add inherited indicator if this is an inherited method
                    method_name = method["name"]
                    
                    method_header = f"#### `{method_name}`"
                    method_header_with_link = add_source_link_to_header(method_header, method_source_link)
                    lines.append(method_header_with_link)
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