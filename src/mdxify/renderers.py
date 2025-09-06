"""Renderers for different output formats (MDX, Markdown)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .formatter import escape_mdx_content
from .source_links import add_source_link_to_header


@dataclass(frozen=True)
class Renderer:
    name: str
    file_extension: str

    def escape(self, content: str) -> str:  # pragma: no cover - simple passthroughs
        return content

    def header_with_source(self, header: str, source_link: Optional[str]) -> str:
        return header

    def frontmatter(self, title: str, sidebar_title: Optional[str] = None) -> list[str]:
        lines = ["---", f"title: {title}"]
        if sidebar_title:
            lines.append(f"sidebarTitle: {sidebar_title}")
        lines.append("---")
        lines.append("")
        return lines


class MDXRenderer(Renderer):
    def __init__(self) -> None:
        super().__init__(name="mdx", file_extension="mdx")

    def escape(self, content: str) -> str:
        return escape_mdx_content(content)

    def header_with_source(self, header: str, source_link: Optional[str]) -> str:
        return add_source_link_to_header(header, source_link)


class MarkdownRenderer(Renderer):
    def __init__(self) -> None:
        super().__init__(name="md", file_extension="md")

    def escape(self, content: str) -> str:
        # Markdown needs minimal escaping; pass through content as-is.
        return content

    def header_with_source(self, header: str, source_link: Optional[str]) -> str:
        if not source_link:
            return header
        # Append a plain markdown link after the header
        return f"{header} [source]({source_link})"


def get_renderer(name: str) -> Renderer:
    name = (name or "mdx").lower()
    if name == "md":
        return MarkdownRenderer()
    return MDXRenderer()

