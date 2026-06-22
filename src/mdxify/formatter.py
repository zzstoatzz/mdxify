"""Docstring formatting utilities."""

import re
import textwrap

from griffe import Docstring

# Pre-compile regex patterns for better performance
# A fence is ``` (optionally indented, optionally with a language) on its own line.
_FENCE_PATTERN = re.compile(r"^\s*```")
# Inline code spans a single line only — MDX does not treat a backtick span that
# wraps across a newline as code, so multi-line backtick content is left to the
# prose escaper (otherwise braces inside it reach MDX unescaped and parse as JSX).
_INLINE_CODE_PATTERN = re.compile(r"`[^`\n]+`")
_TYPE_ANNOTATION_PATTERN = re.compile(
    r"\b(dict|list|tuple|set|type|Optional|Union|Callable|TypeVar|Generic|Literal|Any)\["
)
_ANGLE_BRACKET_PATTERN = re.compile(r"<([^>]+)>")


def _escape_mdx_text(text: str) -> str:
    """Escape a run of non-code text so MDX can't misparse it.

    Handles type-annotation brackets, angle brackets, ``TODO:`` directives, and
    curly braces. Curly braces are MDX expression delimiters, so an unescaped
    ``{...}`` from a docstring (e.g. a dict example) is parsed as JSX and fails.
    """
    # Curly braces first: they're the highest-risk MDX characters. Escaping them
    # before the other rules keeps later replacements from inserting literal
    # braces that we'd then miss.
    text = text.replace("{", "\\{").replace("}", "\\}")
    # Escape square brackets in type annotations outside code blocks
    text = _TYPE_ANNOTATION_PATTERN.sub(r"\1\\[", text)
    # Replace angle brackets with HTML entities to prevent MDX from parsing as tags
    text = _ANGLE_BRACKET_PATTERN.sub(r"&lt;\1&gt;", text)
    # Escape TODO: which can be interpreted as MDX directive
    text = text.replace("TODO:", "TODO\\:")
    return text


def format_docstring_with_griffe(docstring: str, style: str = "google") -> str:
    """Format a docstring using Griffe for better structure.

    Args:
        docstring: The raw docstring text to format.
        style: The docstring style to parse. One of "google", "numpy", or "sphinx".
    """
    if not docstring:
        return ""

    try:
        dedented_docstring = textwrap.dedent(docstring).strip()
        doc = Docstring(dedented_docstring, lineno=1)
        sections = doc.parse(style)  # type: ignore[arg-type]

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

            elif section.kind.value == "attributes" and section.value:
                lines.append("**Attributes:**")
                for attr in section.value:
                    name = attr.name
                    desc = attr.description if hasattr(attr, "description") else ""
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
                # Examples section value is a list of tuples (kind, text)
                if isinstance(section.value, list):
                    for item in section.value:
                        if isinstance(item, tuple) and len(item) == 2:
                            _, text = item
                            lines.append(text.strip())
                        else:
                            lines.append(str(item).strip())
                else:
                    # Fallback for unexpected format
                    lines.append(str(section.value).strip())
                lines.append("")

        return "\n".join(lines)

    except ImportError:
        # Fall back to raw docstring if Griffe not available
        return docstring
    except Exception:
        # If parsing fails, return raw docstring
        return docstring


def _escape_line_outside_code(line: str) -> str:
    """Escape a single non-fenced line, leaving single-line inline code spans alone."""
    parts = []
    last_end = 0
    for match in _INLINE_CODE_PATTERN.finditer(line):
        prose = line[last_end : match.start()]
        if prose:
            parts.append(_escape_mdx_text(prose))
        parts.append(match.group(0))  # inline code, verbatim
        last_end = match.end()
    tail = line[last_end:]
    if tail:
        parts.append(_escape_mdx_text(tail))
    return "".join(parts)


def escape_mdx_content(content: str) -> str:
    """Escape content for MDX to prevent parsing issues, but not inside code.

    Scans line by line so fenced code blocks (```` ``` ````) are tracked with a
    simple state machine. This mirrors how MDX/CommonMark parse fences — including
    auto-closing an unterminated fence at end of input — so braces and other
    MDX-special characters inside code are never escaped, while everything in
    prose is. A regex over the whole string can't do this reliably when fences
    are unbalanced (which Griffe's Examples sections sometimes produce).
    """
    out = []
    in_fence = False
    for line in content.split("\n"):
        if _FENCE_PATTERN.match(line):
            in_fence = not in_fence
            out.append(line)
        elif in_fence:
            out.append(line)
        else:
            out.append(_escape_line_outside_code(line))
    return "\n".join(out)
