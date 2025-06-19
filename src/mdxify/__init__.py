"""mdxify - Generate MDX API documentation from Python modules."""

from .cli import main
from .discovery import find_all_modules, get_module_source_file, should_include_module
from .formatter import escape_mdx_content, format_docstring_with_griffe
from .generator import generate_mdx, is_module_empty
from .navigation import (
    build_hierarchical_navigation,
    get_all_documented_modules,
    update_docs_json,
)
from .parser import extract_docstring, extract_function_signature, parse_module_fast

__all__ = [
    "main",
    "find_all_modules",
    "get_module_source_file",
    "should_include_module",
    "escape_mdx_content",
    "format_docstring_with_griffe",
    "generate_mdx",
    "is_module_empty",
    "build_hierarchical_navigation",
    "get_all_documented_modules",
    "update_docs_json",
    "extract_docstring",
    "extract_function_signature",
    "parse_module_fast",
]
