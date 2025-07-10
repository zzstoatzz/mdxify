"""AST-based module parsing functionality."""

import ast
import re
from pathlib import Path
from typing import Any

# Pre-compile regex for better performance
_RAISES_PATTERN = re.compile(r"^(\s*)Raises\s*$", re.MULTILINE)


def extract_docstring(node: ast.AST) -> str:
    """Extract docstring from an AST node."""
    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value
            # Fix common docstring issues that break MDX parsing
            # Replace "Raises" at the start of a line with "Raises:"
            docstring = _RAISES_PATTERN.sub(r"\1Raises:", docstring)
            return docstring
    return ""


def format_arg(arg: ast.arg) -> str:
    """Format a function argument."""
    result = arg.arg
    if arg.annotation:
        result += f": {ast.unparse(arg.annotation)}"
    return result


def extract_function_signature(node: ast.FunctionDef) -> str:
    """Extract function signature."""
    args = []

    # Regular arguments
    for i, arg in enumerate(node.args.args):
        arg_str = format_arg(arg)
        # Check for defaults
        default_offset = len(node.args.args) - len(node.args.defaults)
        if i >= default_offset:
            default = node.args.defaults[i - default_offset]
            arg_str += f" = {ast.unparse(default)}"
        args.append(arg_str)

    # *args
    if node.args.vararg:
        args.append(f"*{format_arg(node.args.vararg)}")

    # **kwargs
    if node.args.kwarg:
        args.append(f"**{format_arg(node.args.kwarg)}")

    signature = f"{node.name}({', '.join(args)})"

    # Return type
    if node.returns:
        signature += f" -> {ast.unparse(node.returns)}"

    return signature


def parse_module_fast(module_name: str, source_file: Path) -> dict[str, Any]:
    """Parse a module quickly using AST."""
    with open(source_file, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    module_info = {
        "name": module_name,
        "docstring": extract_docstring(tree),
        "classes": [],
        "functions": [],
        "source_file": str(source_file),
    }

    # Only traverse top-level nodes instead of using ast.walk
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            class_info = {
                "name": node.name,
                "docstring": extract_docstring(node),
                "methods": [],
                "line": node.lineno,
            }

            # Extract methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                    method_info = {
                        "name": item.name,
                        "signature": extract_function_signature(item),
                        "docstring": extract_docstring(item),
                        "line": item.lineno,
                    }
                    class_info["methods"].append(method_info)

            module_info["classes"].append(class_info)

        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            # Skip overloaded function definitions
            has_overload = any(
                isinstance(decorator, ast.Name) and decorator.id == "overload"
                for decorator in node.decorator_list
            )
            if not has_overload:
                func_info = {
                    "name": node.name,
                    "signature": extract_function_signature(node),
                    "docstring": extract_docstring(node),
                    "line": node.lineno,
                }
                module_info["functions"].append(func_info)

    return module_info