"""Navigation structure management."""

import json
from pathlib import Path
from typing import Any

from .discovery import should_include_module
from .generator import is_module_empty


def get_all_documented_modules(output_dir: Path) -> list[str]:
    """Get all modules that have documentation files."""
    modules = []
    for mdx_file in output_dir.glob("*.mdx"):
        # Skip non-module files (like index.mdx)
        if "-" not in mdx_file.stem:
            continue
        # Convert filename back to module name
        stem = mdx_file.stem
        # Handle __init__ files
        if stem.endswith("-__init__"):
            module_name = stem[:-9].replace("-", ".")  # Remove -__init__ suffix
        else:
            module_name = stem.replace("-", ".")
        modules.append(module_name)
    return sorted(modules)


def build_hierarchical_navigation(
    generated_modules: list[str], 
    output_dir: Path,
    skip_empty_parents: bool = True
) -> list[dict[str, Any]]:
    """Build a hierarchical navigation structure from flat module names.
    
    Returns a list of navigation entries where each entry is either:
    - A string (the filename without extension for a leaf module)
    - A dict with "group" and "pages" keys for modules with submodules
    """
    # Group modules by their hierarchy
    module_tree = {}
    
    for module_name in sorted(generated_modules):
        parts = module_name.split(".")
        
        if len(parts) == 1:
            # Skip top-level module (just the package name itself)
            continue
            
        # Navigate/create the tree structure
        current = module_tree
        for i, part in enumerate(parts[1:], 1):
            if i == len(parts) - 1:
                # This is the leaf module
                current[part] = {"_is_leaf": True, "_full_name": module_name}
            else:
                # This is an intermediate module
                if part not in current:
                    current[part] = {}
                current = current[part]
    
    def tree_to_nav(tree: dict, parent_parts: list[str] = None) -> list[Any]:
        """Convert the tree structure to navigation format."""
        if parent_parts is None:
            parent_parts = []
            
        result = []
        
        for name, subtree in sorted(tree.items()):
            if subtree.get("_is_leaf"):
                # This is a leaf module - just add the filename
                filename = subtree["_full_name"].replace(".", "-")
                result.append(filename)
            else:
                # This has submodules - create a group
                group_entry = {"group": name, "pages": []}
                
                # Check if this module itself has documentation (as __init__)
                current_parts = parent_parts + [name]
                module_name = ".".join(current_parts)
                init_filename = f"{module_name.replace('.', '-')}-__init__"
                init_file = output_dir / f"{init_filename}.mdx"
                
                if init_file.exists():
                    if not skip_empty_parents or not is_module_empty(init_file):
                        group_entry["pages"].append(init_filename)
                
                # Add all submodules
                sub_pages = tree_to_nav(subtree, current_parts)
                group_entry["pages"].extend(sub_pages)
                
                # Only add the group if it has content
                if group_entry["pages"]:
                    result.append(group_entry)
        
        return result
    
    # Start with the root package name from the first module
    if generated_modules:
        root_package = generated_modules[0].split(".")[0]
        return tree_to_nav(module_tree, [root_package])
    return []


def update_docs_json(
    docs_json_path: Path, 
    generated_modules: list[str], 
    output_dir: Path,
    regenerate_all: bool = False
) -> None:
    """Update docs.json with generated module documentation.
    
    This is Prefect-specific and probably shouldn't be used for other projects.
    Consider using build_hierarchical_navigation directly instead.
    """
    with open(docs_json_path, "r") as f:
        docs_config = json.load(f)

    # Find the API Reference tab
    api_ref_tab = None
    for tab in docs_config.get("navigation", {}).get("tabs", []):
        if tab.get("tab") == "API Reference":
            api_ref_tab = tab
            break

    if not api_ref_tab:
        print("Warning: Could not find API Reference tab in docs.json")
        return

    # API Reference tab uses "groups" not "pages"
    groups = api_ref_tab.get("groups", [])
    if not groups:
        print("Warning: API Reference tab has no groups")
        return

    # Find the main API Reference group
    api_ref_group = None
    for group in groups:
        if group.get("group") == "API Reference":
            api_ref_group = group
            break

    if not api_ref_group:
        print("Warning: Could not find API Reference group")
        return

    # Find or create Python SDK Reference group within the pages
    pages = api_ref_group.get("pages", [])
    sdk_group = None

    for i, page in enumerate(pages):
        if isinstance(page, dict) and page.get("group") == "Python SDK Reference":
            sdk_group = page
            break

    if not sdk_group:
        # Create the group
        sdk_group = {"group": "Python SDK Reference", "pages": []}
        # Insert after the overview page (index.mdx)
        pages.insert(1, sdk_group)

    # Build navigation
    if regenerate_all:
        # Complete regeneration - use only the generated modules
        navigation_pages = build_hierarchical_navigation(generated_modules, output_dir)
    else:
        # Merge mode - get all documented modules and build complete navigation
        all_modules = get_all_documented_modules(output_dir)
        # Filter to only include public modules
        public_modules = [m for m in all_modules if should_include_module(m)]
        navigation_pages = build_hierarchical_navigation(public_modules, output_dir)

    # Need to prepend the path prefix to match existing structure
    # This is the problematic part - it assumes a specific docs structure
    def add_path_prefix(nav_item, prefix="v3/api-ref"):
        if isinstance(nav_item, str):
            return f"{prefix}/{nav_item}"
        elif isinstance(nav_item, dict) and "pages" in nav_item:
            nav_item["pages"] = [add_path_prefix(page, prefix) for page in nav_item["pages"]]
            return nav_item
        return nav_item

    prefixed_pages = [add_path_prefix(page) for page in navigation_pages]
    
    # Always include the Python SDK overview page at the beginning
    sdk_group["pages"] = ["v3/api-ref/python/index"] + prefixed_pages

    # Write back to docs.json
    with open(docs_json_path, "w") as f:
        json.dump(docs_config, f, indent=2)
        f.write("\n")  # Add trailing newline