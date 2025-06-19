"""Navigation structure management."""

import json
from pathlib import Path
from typing import Any

from .generator import is_module_empty


def get_all_documented_modules(output_dir: Path) -> list[str]:
    """Get all modules that have documentation files."""
    modules = []
    for mdx_file in output_dir.glob("prefect-*.mdx"):
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
    generated_modules: list[str], skip_empty_parents: bool = True
) -> list[Any]:
    """Build a hierarchical navigation structure from flat module names."""
    # Group modules by top-level module
    module_tree = {}

    for module_name in sorted(generated_modules):
        parts = module_name.split(".")

        if len(parts) == 1:
            # Top-level module (e.g., 'prefect')
            continue
        elif len(parts) == 2:
            # Direct module (e.g., 'prefect.flows')
            module_tree[parts[1]] = {
                "path": f"v3/api-ref/{module_name.replace('.', '-')}",
                "submodules": {},
            }
        else:
            # Submodule (e.g., 'prefect.blocks.core')
            top_module = parts[1]
            if top_module not in module_tree:
                module_tree[top_module] = {
                    "path": f"v3/api-ref/prefect-{top_module}",
                    "submodules": {},
                }

            # Build nested structure
            current = module_tree[top_module]["submodules"]
            for i, part in enumerate(parts[2:], 2):
                if i == len(parts) - 1:
                    # Leaf node
                    current[part] = {
                        "path": f"v3/api-ref/{module_name.replace('.', '-')}",
                        "submodules": {},
                    }
                else:
                    # Intermediate node
                    if part not in current:
                        current[part] = {"path": None, "submodules": {}}
                    current = current[part]["submodules"]

    # Convert tree to navigation format
    def tree_to_nav(tree: dict, level: int = 0) -> list[Any]:
        result = []

        for name, info in sorted(tree.items()):
            if info["submodules"]:
                # Has submodules - create a group
                group_entry = {"group": name, "pages": []}

                # If the parent module has content, add it as __init__ inside the group
                if info["path"]:
                    # Check if the file exists with __init__ suffix
                    parent_path = info["path"] + "-__init__"
                    module_file = Path(
                        parent_path.replace("v3/api-ref/", "docs/v3/api-ref/") + ".mdx"
                    )

                    if module_file.exists():
                        if skip_empty_parents:
                            if not is_module_empty(module_file):
                                group_entry["pages"].append(parent_path)
                        else:
                            group_entry["pages"].append(parent_path)
                    else:
                        # Try the original path (for backwards compatibility)
                        module_file = Path(
                            info["path"].replace("v3/api-ref/", "docs/v3/api-ref/")
                            + ".mdx"
                        )
                        if module_file.exists():
                            if skip_empty_parents:
                                if not is_module_empty(module_file):
                                    group_entry["pages"].append(info["path"])
                            else:
                                group_entry["pages"].append(info["path"])

                # Add submodules
                group_entry["pages"].extend(tree_to_nav(info["submodules"], level + 1))

                # Only add the group if it has pages
                if group_entry["pages"]:
                    result.append(group_entry)
            else:
                # No submodules - just add the path
                if info["path"]:
                    result.append(info["path"])

        return result

    return tree_to_nav(module_tree)


def update_docs_json(
    docs_json_path: Path, generated_modules: list[str], regenerate_all: bool = False
) -> None:
    """Update docs.json with generated module documentation.
    Args:
        docs_json_path: Path to docs.json file
        generated_modules: List of modules that were just generated
        regenerate_all: If True, completely regenerate the navigation. If False, merge with existing.
    """
    docs_config = json.loads(docs_json_path.read_text())

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
        navigation_pages = build_hierarchical_navigation(generated_modules)
    else:
        # Merge mode - get all documented modules and build complete navigation
        from .discovery import should_include_module

        output_dir = Path("docs/v3/api-ref")
        all_modules = get_all_documented_modules(output_dir)
        # Filter to only include public modules
        public_modules = [m for m in all_modules if should_include_module(m)]
        navigation_pages = build_hierarchical_navigation(public_modules)

    # Always include the Python SDK overview page at the beginning
    sdk_group["pages"] = ["v3/api-ref/python/index"] + navigation_pages

    # Write back to docs.json
    docs_json_path.write_text(json.dumps(docs_config, indent=2) + "\n")
