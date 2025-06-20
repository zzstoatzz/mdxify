"""Tests for the navigation module."""

import json

from mdxify.navigation import (
    build_hierarchical_navigation,
    find_mdxify_placeholder,
    update_docs_json,
)


def test_build_hierarchical_navigation_simple(tmp_path):
    """Test building navigation for simple module structure."""
    modules = [
        "mypackage.flows",
        "mypackage.tasks",
        "mypackage.blocks.core",
        "mypackage.blocks.system",
    ]
    
    result = build_hierarchical_navigation(modules, tmp_path, skip_empty_parents=False)
    
    # Should have three top-level entries: flows, tasks, and blocks group
    assert len(result) == 3
    
    # Find the blocks group
    blocks_group = None
    for item in result:
        if isinstance(item, dict) and item.get("group") == "blocks":
            blocks_group = item
            break
    
    assert blocks_group is not None
    assert len(blocks_group["pages"]) >= 2  # core and system


def test_build_hierarchical_navigation_nested(tmp_path):
    """Test building navigation for deeply nested modules."""
    # Create a structure where parent modules aren't included
    modules = [
        "mypackage.utils.helpers",
        "mypackage.utils.validators", 
        "mypackage.models.base",
        "mypackage.models.user",
    ]
    
    result = build_hierarchical_navigation(modules, tmp_path, skip_empty_parents=False)
    
    # Should have 2 groups: utils and models
    assert len(result) == 2
    
    # Both should be groups (dicts with 'group' key)
    assert all(isinstance(item, dict) and "group" in item for item in result)
    
    # Check group names
    group_names = {item["group"] for item in result}
    assert "utils" in group_names
    assert "models" in group_names


def test_find_mdxify_placeholder():
    """Test finding the mdxify placeholder in various structures."""
    # Simple case - in a list
    doc = {
        "navigation": [
            {"group": "Guide", "pages": ["intro", "setup"]},
            {"group": "API", "pages": [
                "overview",
                {"$mdxify": "generated"},
                "advanced"
            ]}
        ]
    }
    
    result = find_mdxify_placeholder(doc)
    assert result is not None
    container_info, path = result
    container, index = container_info
    assert isinstance(container, list)
    assert index == 1
    assert container[index] == {"$mdxify": "generated"}
    
    # Not found case
    doc = {"navigation": [{"group": "Guide", "pages": ["intro"]}]}
    result = find_mdxify_placeholder(doc)
    assert result is None


def test_update_docs_json_with_placeholder(tmp_path):
    """Test updating docs.json when placeholder exists."""
    # Create a docs.json with placeholder
    docs_json = tmp_path / "docs.json"
    docs_config = {
        "name": "Test Project",
        "navigation": [
            {
                "group": "Getting Started",
                "pages": ["intro", "install"]
            },
            {
                "group": "API Reference",
                "pages": [
                    "api/overview",
                    {"$mdxify": "generated"},
                    "api/advanced"
                ]
            }
        ]
    }
    
    with open(docs_json, "w") as f:
        json.dump(docs_config, f)
    
    # Create some dummy MDX files
    output_dir = tmp_path / "api"
    output_dir.mkdir()
    (output_dir / "mypackage-core.mdx").write_text("# Core")
    (output_dir / "mypackage-utils.mdx").write_text("# Utils")
    
    # Update docs.json
    generated_modules = ["mypackage.core", "mypackage.utils"]
    update_docs_json(docs_json, generated_modules, output_dir, regenerate_all=True)
    
    # Check the result
    with open(docs_json) as f:
        updated_config = json.load(f)
    
    api_pages = updated_config["navigation"][1]["pages"]
    # Should have: overview, core, utils, advanced
    assert len(api_pages) == 4
    assert api_pages[0] == "api/overview"
    assert "api/mypackage-core" in api_pages
    assert "api/mypackage-utils" in api_pages
    assert api_pages[-1] == "api/advanced"


def test_update_docs_json_without_placeholder(tmp_path, capsys):
    """Test updating docs.json when placeholder doesn't exist."""
    # Create a docs.json without placeholder
    docs_json = tmp_path / "docs.json"
    docs_config = {
        "name": "Test Project",
        "navigation": [
            {
                "group": "Getting Started",
                "pages": ["intro", "install"]
            }
        ]
    }
    
    with open(docs_json, "w") as f:
        json.dump(docs_config, f)
    
    output_dir = tmp_path / "api"
    output_dir.mkdir()
    
    # Update docs.json
    update_docs_json(docs_json, [], output_dir)
    
    # Should print warning
    captured = capsys.readouterr()
    assert "Could not find mdxify placeholder" in captured.out
    assert '{"$mdxify": "generated"}' in captured.out