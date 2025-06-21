"""Module discovery utilities."""

import importlib
import importlib.util
import pkgutil
from pathlib import Path
from typing import Optional


def get_module_source_file(module_name: str) -> Optional[Path]:
    """Get the source file path for a module."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin:
            return Path(spec.origin)
    except Exception:
        pass
    return None


def find_all_modules(root_module: str) -> list[str]:
    """Find all modules under a root module."""
    modules = []

    try:
        root = importlib.import_module(root_module)
        if hasattr(root, "__path__"):
            for importer, modname, ispkg in pkgutil.walk_packages(
                root.__path__, prefix=root_module + "."
            ):
                modules.append(modname)
    except ImportError:
        pass

    return sorted(modules)


def should_include_module(module_name: str) -> bool:
    """Check if a module should be included in the API documentation."""
    parts = module_name.split(".")

    # Exclude any module or submodule that starts with underscore
    for part in parts[1:]:  # Skip the root module
        if part.startswith("_"):
            return False

    return True