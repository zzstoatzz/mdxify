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


def extract_function_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef, *, skip_first_arg: bool = False
) -> str:
    """Extract a signature, optionally omitting a bound positional receiver."""
    args = []

    positional = node.args.posonlyargs + node.args.args
    default_offset = len(positional) - len(node.args.defaults)
    start = 1 if skip_first_arg and positional else 0
    for i, arg in enumerate(positional):
        if i < start:
            continue
        arg_str = format_arg(arg)
        if i >= default_offset:
            default = node.args.defaults[i - default_offset]
            arg_str += f" = {ast.unparse(default)}"
        args.append(arg_str)
        if i == len(node.args.posonlyargs) - 1:
            args.append("/")

    if node.args.vararg:
        args.append(f"*{format_arg(node.args.vararg)}")
    elif node.args.kwonlyargs:
        args.append("*")

    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        arg_str = format_arg(arg)
        if default is not None:
            arg_str += f" = {ast.unparse(default)}"
        args.append(arg_str)

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


def _builtin_decorator_name(decorator: ast.expr) -> str | None:
    """Recognize conventional built-in decorator names without resolving imports."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    if (
        isinstance(decorator, ast.Attribute)
        and isinstance(decorator.value, ast.Name)
        and decorator.value.id == "builtins"
    ):
        return decorator.attr
    return None


def _member_binding_names(item: ast.stmt) -> set[str]:
    """Collect names bound directly in a class body, excluding type-only hints."""
    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {item.name}
    if isinstance(item, ast.Assign):
        targets = item.targets
    elif isinstance(item, ast.AnnAssign) and item.value is not None:
        targets = [item.target]
    else:
        return set()
    return {
        node.id
        for target in targets
        for node in ast.walk(target)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }


def extract_class_members(
    node: ast.ClassDef, include_internal: bool = False
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract methods and aggregate conventional same-name property accessors."""
    methods: list[dict[str, Any]] = []
    properties: dict[str, dict[str, Any]] = {}
    for item in node.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for name in _member_binding_names(item):
                properties.pop(name, None)
            continue
        if not include_internal and item.name.startswith("_"):
            continue

        decorators = {_builtin_decorator_name(d) for d in item.decorator_list}
        if "property" in decorators:
            methods = [method for method in methods if method["name"] != item.name]
            properties[item.name] = {
                "name": item.name,
                "annotation": ast.unparse(item.returns) if item.returns else None,
                "docstring": extract_docstring(item),
                "line": item.lineno,
                "has_setter": False,
                "has_deleter": False,
                "setter_docstring": "",
                "deleter_docstring": "",
                "is_inherited": False,
            }
            continue

        accessor = next((
            d.attr for d in item.decorator_list
            if isinstance(d, ast.Attribute)
            and isinstance(d.value, ast.Name)
            and d.value.id == item.name
            and item.name in properties
            and d.attr in {"getter", "setter", "deleter"}
        ), None)
        if accessor:
            prop = properties[item.name]
            if accessor == "getter":
                prop["annotation"] = ast.unparse(item.returns) if item.returns else None
                prop["docstring"] = extract_docstring(item)
                prop["line"] = item.lineno
            else:
                prop[f"has_{accessor}"] = True
                prop[f"{accessor}_docstring"] = extract_docstring(item)
            continue

        properties.pop(item.name, None)
        if "staticmethod" in decorators:
            kind = "static"
        elif "classmethod" in decorators:
            kind = "class"
        else:
            kind = "instance"
        methods.append({
            "name": item.name,
            "signature": extract_function_signature(item, skip_first_arg=kind == "class"),
            "docstring": extract_docstring(item),
            "line": item.lineno,
            "is_inherited": False,
            "kind": kind,
        })
    return methods, list(properties.values())


def extract_methods_from_class(node: ast.ClassDef, include_internal: bool = False) -> list[dict[str, Any]]:
    """Extract callable methods, excluding property accessors."""
    return extract_class_members(node, include_internal)[0]


def _class_member_names(node: ast.ClassDef) -> set[str]:
    """Collect local bindings that shadow inherited members, before filtering."""
    return {name for item in node.body for name in _member_binding_names(item)}


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
        return self._get_inherited_members(class_name, include_internal)[0]

    def get_inherited_properties(self, class_name: str, include_internal: bool = False) -> list[dict[str, Any]]:
        """Get inherited properties for a class."""
        return self._get_inherited_members(class_name, include_internal)[1]

    def _get_inherited_members(
        self, class_name: str, include_internal: bool
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Copy direct-base members with first-base precedence across kinds."""
        if class_name not in self.classes:
            return [], []
        
        class_info = self.classes[class_name]
        base_classes = class_info.get("base_classes", [])
        inherited_methods: list[dict[str, Any]] = []
        inherited_properties: list[dict[str, Any]] = []
        processed_members: set[str] = set()
        
        # Get all available modules for base class resolution
        available_modules = list(self.module_classes.keys())
        
        for base_class in base_classes:
            # Try to find the base class in available modules
            base_full_name = self.find_class_in_modules(base_class, available_modules)
            if base_full_name and base_full_name in self.classes:
                base_info = self.classes[base_full_name]
                base_source_file = self.class_source_files.get(base_full_name)
                for key, result in (("methods", inherited_methods), ("properties", inherited_properties)):
                    for member in base_info.get(key, []):
                        name = member["name"]
                        if name in processed_members:
                            continue
                        processed_members.add(name)
                        if not include_internal and name.startswith("_"):
                            continue
                        inherited_member = member.copy()
                        inherited_member["is_inherited"] = True
                        inherited_member["inherited_from"] = base_class
                        if base_source_file:
                            inherited_member["source_file"] = base_source_file
                        result.append(inherited_member)
                processed_members.update(base_info.get("member_names", []))
        
        return inherited_methods, inherited_properties


def parse_module_fast(module_name: str, source_file: Path, include_internal: bool = False, 
                     class_registry: ClassRegistry | None = None) -> dict[str, Any]:
    """Parse a module quickly using AST."""
    with open(source_file, "r", encoding="utf-8", newline="") as f:
        source = f.read()
    
    # Normalize line endings to ensure consistent AST line numbers across platforms
    source = source.replace("\r\n", "\n").replace("\r", "\n")

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
            methods, properties = extract_class_members(node, include_internal)
            class_info = {
                "name": node.name,
                "docstring": extract_docstring(node),
                "methods": methods,
                "properties": properties,
                "member_names": _class_member_names(node),
                "line": node.lineno,
                "base_classes": extract_base_classes(node),
            }

            # Add inherited methods if we have a class registry
            if class_registry:
                local_names = class_info["member_names"]
                inherited_methods = class_registry.get_inherited_methods(f"{module_name}.{node.name}", include_internal)
                inherited_properties = class_registry.get_inherited_properties(f"{module_name}.{node.name}", include_internal)
                class_info["methods"].extend(m for m in inherited_methods if m["name"] not in local_names)
                class_info["properties"].extend(p for p in inherited_properties if p["name"] not in local_names)
                # Sort methods by name for consistent output
                class_info["methods"].sort(key=lambda m: m["name"])
                class_info["properties"].sort(key=lambda p: p["name"])

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
            with open(source_file, "r", encoding="utf-8", newline="") as f:
                source = f.read()
            # Normalize line endings to ensure consistent AST line numbers across platforms
            source = source.replace("\r\n", "\n").replace("\r", "\n")
            tree = ast.parse(source)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    # For the registry, we want ALL classes (including private ones)
                    methods, properties = extract_class_members(node, include_internal)
                    class_info = {
                        "name": node.name,
                        "docstring": extract_docstring(node),
                        "methods": methods,
                        "properties": properties,
                        "member_names": _class_member_names(node),
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
