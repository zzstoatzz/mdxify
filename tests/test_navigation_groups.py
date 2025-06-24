"""Test navigation update with groups (not just anchors)."""

import json

from mdxify.navigation import find_mdxify_anchor_or_group, update_docs_json


def test_find_anchor_or_group_finds_anchors():
    """Test that find_mdxify_anchor_or_group finds anchors."""
    docs_config = {
        "navigation": {
            "tabs": [
                {
                    "tab": "SDK Reference",
                    "anchors": [
                        {
                            "anchor": "Python SDK",
                            "icon": "python",
                            "pages": [
                                "python-sdk/module1",
                                "python-sdk/module2"
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    result = find_mdxify_anchor_or_group(docs_config, "Python SDK")
    assert result is not None
    container_info, path = result
    container, index = container_info
    assert container == ["python-sdk/module1", "python-sdk/module2"]
    assert index is None  # No placeholder found


def test_find_anchor_or_group_finds_groups():
    """Test that find_mdxify_anchor_or_group finds groups."""
    docs_config = {
        "navigation": {
            "tabs": [
                {
                    "tab": "API Reference",
                    "groups": [
                        {
                            "group": "API Reference",
                            "pages": [
                                "api-ref/index",
                                {
                                    "group": "Python SDK Reference",
                                    "pages": [
                                        "api-ref/python/module1",
                                        "api-ref/python/module2"
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    result = find_mdxify_anchor_or_group(docs_config, "Python SDK Reference")
    assert result is not None
    container_info, path = result
    container, index = container_info
    assert container == ["api-ref/python/module1", "api-ref/python/module2"]
    assert index is None  # No placeholder found


def test_update_docs_json_with_group(tmp_path):
    """Test updating docs.json when target is a group, not an anchor."""
    # Create a docs.json with group structure like Prefect uses
    docs_json = tmp_path / "docs.json"
    docs_config = {
        "name": "Prefect",
        "navigation": {
            "tabs": [
                {
                    "tab": "API Reference",
                    "groups": [
                        {
                            "group": "API Reference",
                            "pages": [
                                "api-ref/index",
                                {
                                    "group": "Python SDK Reference",
                                    "pages": [
                                        {"$mdxify": "generated"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    with open(docs_json, "w") as f:
        json.dump(docs_config, f, indent=2)
    
    # Create output directory with some generated files
    output_dir = tmp_path / "python-sdk"
    output_dir.mkdir()
    
    # Create some MDX files
    (output_dir / "mypackage-core.mdx").write_text("# Core Module")
    (output_dir / "mypackage-utils.mdx").write_text("# Utils Module")
    
    # Update navigation
    result = update_docs_json(
        docs_json,
        ["mypackage.core", "mypackage.utils"],
        output_dir,
        regenerate_all=True,
        anchor_name="Python SDK Reference"
    )
    
    assert result is True
    
    # Load and check the updated navigation
    with open(docs_json) as f:
        updated = json.load(f)
    
    # Navigate to the group
    group_pages = None
    for tab in updated["navigation"]["tabs"]:
        if tab["tab"] == "API Reference":
            for group in tab["groups"]:
                if group["group"] == "API Reference":
                    for page in group["pages"]:
                        if isinstance(page, dict) and page.get("group") == "Python SDK Reference":
                            group_pages = page["pages"]
                            break
    
    assert group_pages is not None
    assert len(group_pages) == 2
    assert "python-sdk/mypackage-core" in group_pages
    assert "python-sdk/mypackage-utils" in group_pages


def test_backwards_compatibility_find_mdxify_anchor():
    """Test that the old find_mdxify_anchor function still works and finds groups too."""
    from mdxify.navigation import find_mdxify_anchor
    
    # Test with a group
    docs_config = {
        "navigation": {
            "tabs": [
                {
                    "tab": "API Reference",
                    "groups": [
                        {
                            "group": "Python SDK Reference",
                            "pages": ["module1", "module2"]
                        }
                    ]
                }
            ]
        }
    }
    
    # The old function should now find groups too
    result = find_mdxify_anchor(docs_config, "Python SDK Reference")
    assert result is not None