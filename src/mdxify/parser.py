"""AST-based module parsing functionality."""

import ast
import re
from pathlib import Path
from typing import Any, Optional

# Pre-compile regex for better performance
_RAISES_PATTERN = re.compile(r"^(\s*)Raises\s*$", re.MULTILINE)


def extract_docstring(node: ast.AST) -> str:
    """Extract docstring from an AST node."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
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


def extract_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
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


def extract_base_classes(node: ast.ClassDef) -> list[str]:
    """Extract base class names from a class definition."""
    base_classes = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            base_classes.append(base.id)
        elif isinstance(base, ast.Attribute):
            # Handle cases like 'module.ClassName'
            parts = []
            current = base
            while isinstance(current, ast.Attribute):
                parts.insert(0, current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.insert(0, current.id)
                base_classes.append(".".join(parts))
    return base_classes


def extract_methods_from_class(node: ast.ClassDef, include_internal: bool = False) -> list[dict[str, Any]]:
    """Extract methods from a class definition."""
    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and (include_internal or not item.name.startswith("_")):
            method_info = {
                "name": item.name,
                "signature": extract_function_signature(item),
                "docstring": extract_docstring(item),
                "line": item.lineno,
                "is_inherited": False,
            }
            methods.append(method_info)
    return methods


class ClassRegistry:
    """Registry for tracking classes and their inheritance relationships."""
    
    def __init__(self):
        self.classes: dict[str, dict[str, Any]] = {}
        self.module_classes: dict[str, list[str]] = {}  # module_name -> list of class names
        self.class_source_files: dict[str, str] = {}  # full_class_name -> source_file
    
    def add_class(self, module_name: str, class_name: str, class_info: dict[str, Any], source_file: Optional[str] = None):
        """Add a class to the registry."""
        full_name = f"{module_name}.{class_name}"
        self.classes[full_name] = class_info
        if module_name not in self.module_classes:
            self.module_classes[module_name] = []
        self.module_classes[module_name].append(class_name)
        if source_file:
            self.class_source_files[full_name] = source_file
    
    def get_class(self, class_name: str) -> dict[str, Any] | None:
        """Get a class by its full name."""
        return self.classes.get(class_name)
    
    def find_class_in_modules(self, class_name: str, modules: list[str]) -> str | None:
        """Find a class by name across a list of modules."""
        for module in modules:
            full_name = f"{module}.{class_name}"
            if full_name in self.classes:
                return full_name
        return None
    
    def get_inherited_methods(self, class_name: str, include_internal: bool = False) -> list[dict[str, Any]]:
        """Get inherited methods for a class."""
        if class_name not in self.classes:
            return []
        
        class_info = self.classes[class_name]
        base_classes = class_info.get("base_classes", [])
        inherited_methods = []
        processed_methods: set[str] = set()
        
        # Get all available modules for base class resolution
        available_modules = list(self.module_classes.keys())
        
        for base_class in base_classes:
            # Try to find the base class in available modules
            base_full_name = self.find_class_in_modules(base_class, available_modules)
            if base_full_name and base_full_name in self.classes:
                base_methods = self.classes[base_full_name].get("methods", [])
                base_source_file = self.class_source_files.get(base_full_name)
                for method in base_methods:
                    if method["name"] not in processed_methods:
                        # Create a copy of the method info and mark as inherited
                        inherited_method = method.copy()
                        inherited_method["is_inherited"] = True
                        inherited_method["inherited_from"] = base_class
                        # Add source file information from the parent class
                        if base_source_file:
                            inherited_method["source_file"] = base_source_file
                        inherited_methods.append(inherited_method)
                        processed_methods.add(method["name"])
        
        return inherited_methods


def parse_module_fast(module_name: str, source_file: Path, include_internal: bool = False, 
                     class_registry: ClassRegistry | None = None) -> dict[str, Any]:
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
        if isinstance(node, ast.ClassDef) and (include_internal or not node.name.startswith("_")):
            class_info = {
                "name": node.name,
                "docstring": extract_docstring(node),
                "methods": extract_methods_from_class(node, include_internal),
                "line": node.lineno,
                "base_classes": extract_base_classes(node),
            }

            # Add inherited methods if we have a class registry
            if class_registry:
                inherited_methods = class_registry.get_inherited_methods(f"{module_name}.{node.name}", include_internal)
                class_info["methods"].extend(inherited_methods)
                # Sort methods by name for consistent output
                class_info["methods"].sort(key=lambda m: m["name"])

            module_info["classes"].append(class_info)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (include_internal or not node.name.startswith("_")):
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


def parse_modules_with_inheritance(modules_to_process: list[str], include_internal: bool = False) -> dict[str, dict[str, Any]]:
    """Parse multiple modules with inheritance support, including parent classes in private modules."""
    from .cli import should_include_module
    from .discovery import find_all_modules, get_module_source_file

    # First pass: build class registry from ALL available modules (including private ones)
    # This ensures we can find parent classes even if they're in private modules
    class_registry = ClassRegistry()

    # Get the root module from the first module to process
    root_module = None
    if modules_to_process:
        root_module = modules_to_process[0].split(".")[0]
    # Find all modules under the root (including private ones)
    all_modules = []
    if root_module:
        all_modules = find_all_modules(root_module)
    # Add the explicitly requested modules in case they're not found by find_all_modules
    all_modules.extend(modules_to_process)
    all_modules = sorted(set(all_modules))  # Remove duplicates

    for module_name in all_modules:
        source_file = get_module_source_file(module_name)
        if not source_file:
            continue
        try:
            with open(source_file, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    # For the registry, we want ALL classes (including private ones)
                    # but only public methods from them
                    class_info = {
                        "name": node.name,
                        "docstring": extract_docstring(node),
                        "methods": extract_methods_from_class(node, include_internal=False),  # Always public methods only
                        "line": node.lineno,
                        "base_classes": extract_base_classes(node),
                    }
                    class_registry.add_class(module_name, node.name, class_info, str(source_file))
        except Exception:
            # Skip modules that can't be parsed
            continue

    # Second pass: parse only the requested modules with inheritance
    module_results = {}
    for module_name in modules_to_process:
        if not should_include_module(module_name, include_internal):
            continue
        source_file = get_module_source_file(module_name)
        if source_file:
            try:
                module_info = parse_module_fast(module_name, Path(source_file), include_internal, class_registry)
                module_results[module_name] = module_info
            except Exception:
                # Skip modules that can't be parsed
                continue

    return module_results