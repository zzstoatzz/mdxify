"""Docstring formatting utilities."""

import re
import textwrap

from griffe import Docstring


def format_docstring_with_griffe(docstring: str) -> str:
    """Format a docstring using Griffe for better structure."""
    if not docstring:
        return ""

    try:
        dedented_docstring = textwrap.dedent(docstring).strip()
        doc = Docstring(dedented_docstring, lineno=1)
        sections = doc.parse("google")

        lines = []

        for section in sections:
            if section.kind.value == "text":
                # Main description
                lines.append(section.value.strip())
                lines.append("")

            elif section.kind.value == "parameters" and section.value:
                lines.append("**Args:**")
                for param in section.value:
                    name = param.name
                    desc = param.description if hasattr(param, "description") else ""
                    # Escape colons in the description to prevent Markdown definition list interpretation
                    desc = desc.replace(":", "\\:")
                    # Format as a list item
                    lines.append(f"- `{name}`: {desc}")
                lines.append("")

            elif section.kind.value == "returns" and section.value:
                lines.append("**Returns:**")
                # Returns can be a list of return values
                if hasattr(section.value, "__iter__"):
                    for ret in section.value:
                        desc = (
                            ret.description if hasattr(ret, "description") else str(ret)
                        )
                        lines.append(f"- {desc}")
                else:
                    desc = (
                        section.value.description
                        if hasattr(section.value, "description")
                        else str(section.value)
                    )
                    lines.append(desc)
                lines.append("")

            elif section.kind.value == "raises" and section.value:
                lines.append("**Raises:**")
                for exc in section.value:
                    name = exc.annotation if hasattr(exc, "annotation") else ""
                    desc = exc.description if hasattr(exc, "description") else ""
                    # Escape colons in the description to prevent Markdown definition list interpretation
                    desc = desc.replace(":", "\\:")
                    lines.append(f"- `{name}`: {desc}")
                lines.append("")

            elif section.kind.value == "examples" and section.value:
                lines.append("**Examples:**")
                lines.append("")
                lines.append("```python")
                lines.append(section.value.strip())
                lines.append("```")
                lines.append("")

        return "\n".join(lines)

    except ImportError:
        # Fall back to raw docstring if Griffe not available
        return docstring
    except Exception:
        # If parsing fails, return raw docstring
        return docstring


def escape_mdx_content(content: str) -> str:
    """Escape content for MDX to prevent parsing issues, but not inside code blocks."""
    # Split content by code blocks to avoid escaping inside them
    # Pattern matches both inline code (`...`) and code blocks (```...```)
    parts = []
    last_end = 0

    # Find all code blocks and inline code
    code_block_pattern = r"(```[\s\S]*?```|`[^`]+`)"

    for match in re.finditer(code_block_pattern, content):
        # Add the text before the code block (escaped)
        text_before = content[last_end : match.start()]
        if text_before:
            # Escape square brackets in type annotations outside code blocks
            text_before = re.sub(
                r"\b(dict|list|tuple|set|type|Optional|Union|Callable|TypeVar|Generic|Literal|Any)\[",
                r"\1\\[",
                text_before,
            )
            # Replace angle brackets with HTML entities to prevent MDX from parsing as tags
            text_before = re.sub(r"<([^>]+)>", r"&lt;\1&gt;", text_before)
            # Escape TODO: which can be interpreted as MDX directive
            text_before = text_before.replace("TODO:", "TODO\\:")
        parts.append(text_before)

        # Add the code block itself (unescaped)
        parts.append(match.group(0))

        last_end = match.end()

    # Add any remaining text after the last code block (escaped)
    remaining_text = content[last_end:]
    if remaining_text:
        remaining_text = re.sub(
            r"\b(dict|list|tuple|set|type|Optional|Union|Callable|TypeVar|Generic|Literal|Any)\[",
            r"\1\\[",
            remaining_text,
        )
        # Replace angle brackets with HTML entities to prevent MDX from parsing as tags
        remaining_text = re.sub(r"<([^>]+)>", r"&lt;\1&gt;", remaining_text)
        # Escape TODO: which can be interpreted as MDX directive
        remaining_text = remaining_text.replace("TODO:", "TODO\\:")
    parts.append(remaining_text)

    return "".join(parts)
