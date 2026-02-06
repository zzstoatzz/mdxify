"""Test navigation update with groups (not just anchors), and Mintlify versions."""

import json

from mdxify.navigation import (
    _find_version_entry,
    find_mdxify_anchor_or_group,
    update_docs_json,
)


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


# --- Mintlify versions support ---


def _versioned_docs_config():
    """Reusable config mimicking FastMCP's versioned navigation."""
    return {
        "name": "FastMCP",
        "navigation": {
            "versions": [
                {
                    "version": "v3.0.0",
                    "dropdowns": [
                        {
                            "dropdown": "Documentation",
                            "groups": [
                                {"group": "Get Started", "pages": ["getting-started/welcome"]}
                            ],
                            "icon": "book",
                        },
                        {
                            "dropdown": "SDK Reference",
                            "anchors": [
                                {
                                    "anchor": "Python SDK",
                                    "icon": "python",
                                    "pages": ["python-sdk/old-module"],
                                }
                            ],
                            "icon": "code",
                        },
                    ],
                },
                {
                    "version": "v2.14.3",
                    "dropdowns": [
                        {
                            "dropdown": "Documentation",
                            "groups": [
                                {"group": "Get Started", "pages": ["v2/getting-started/welcome"]}
                            ],
                            "icon": "book",
                        }
                    ],
                },
            ]
        },
    }


def test_find_version_entry():
    """Test _find_version_entry locates the right version."""
    nav = _versioned_docs_config()["navigation"]
    assert _find_version_entry(nav, "v3.0.0") is not None
    assert _find_version_entry(nav, "v3.0.0")["version"] == "v3.0.0"
    assert _find_version_entry(nav, "v2.14.3") is not None
    assert _find_version_entry(nav, "v2.14.3")["version"] == "v2.14.3"
    assert _find_version_entry(nav, "v999") is None


def test_find_version_entry_no_versions():
    """Test _find_version_entry when navigation has no versions key."""
    assert _find_version_entry({"tabs": []}, "v1") is None
    assert _find_version_entry([], "v1") is None  # type: ignore[arg-type]


def test_find_anchor_scoped_to_version():
    """Test that mintlify_version constrains the search to the right version."""
    config = _versioned_docs_config()

    # v3 has "Python SDK"; searching within v3 should find it
    result = find_mdxify_anchor_or_group(config, "Python SDK", mintlify_version="v3.0.0")
    assert result is not None
    pages, _path = result
    container, _index = pages
    assert "python-sdk/old-module" in container

    # v2 does NOT have "Python SDK"; searching within v2 should return None
    result = find_mdxify_anchor_or_group(config, "Python SDK", mintlify_version="v2.14.3")
    assert result is None


def test_find_anchor_nonexistent_version():
    """Test that a non-existent mintlify_version returns None."""
    config = _versioned_docs_config()
    result = find_mdxify_anchor_or_group(config, "Python SDK", mintlify_version="v999")
    assert result is None


def test_find_anchor_without_version_searches_everything():
    """Test that omitting mintlify_version preserves the old full-tree search."""
    config = _versioned_docs_config()
    result = find_mdxify_anchor_or_group(config, "Python SDK")
    assert result is not None


def test_update_docs_json_versioned(tmp_path):
    """Test full update_docs_json targeting a specific Mintlify version."""
    docs_json = tmp_path / "docs.json"
    config = _versioned_docs_config()
    docs_json.write_text(json.dumps(config, indent=2))

    output_dir = tmp_path / "python-sdk"
    output_dir.mkdir()
    (output_dir / "fastmcp-client.mdx").write_text("# Client")
    (output_dir / "fastmcp-server.mdx").write_text("# Server")

    result = update_docs_json(
        docs_json,
        ["fastmcp.client", "fastmcp.server"],
        output_dir,
        regenerate_all=True,
        anchor_name="Python SDK",
        mintlify_version="v3.0.0",
    )
    assert result is True

    with open(docs_json) as f:
        updated = json.load(f)

    # The v3 SDK Reference should be updated
    v3 = updated["navigation"]["versions"][0]
    sdk_dropdown = next(d for d in v3["dropdowns"] if d["dropdown"] == "SDK Reference")
    sdk_anchor = sdk_dropdown["anchors"][0]
    assert sdk_anchor["anchor"] == "Python SDK"
    assert "python-sdk/fastmcp-client" in sdk_anchor["pages"]
    assert "python-sdk/fastmcp-server" in sdk_anchor["pages"]
    assert "python-sdk/old-module" not in sdk_anchor["pages"]
    assert sdk_anchor["icon"] == "python"  # preserved

    # The v2 docs should be completely untouched
    v2 = updated["navigation"]["versions"][1]
    assert v2 == config["navigation"]["versions"][1]


def test_update_docs_json_versioned_wrong_version(tmp_path, capsys):
    """Test that targeting a version without the anchor fails gracefully."""
    docs_json = tmp_path / "docs.json"
    config = _versioned_docs_config()
    docs_json.write_text(json.dumps(config, indent=2))

    output_dir = tmp_path / "python-sdk"
    output_dir.mkdir()

    result = update_docs_json(
        docs_json,
        ["fastmcp.client"],
        output_dir,
        regenerate_all=True,
        anchor_name="Python SDK",
        mintlify_version="v2.14.3",
    )
    assert result is False
    captured = capsys.readouterr()
    assert "does not contain" in captured.out


def test_update_docs_json_versioned_nonexistent_version(tmp_path, capsys):
    """Test that targeting a non-existent version fails with helpful message."""
    docs_json = tmp_path / "docs.json"
    config = _versioned_docs_config()
    docs_json.write_text(json.dumps(config, indent=2))

    output_dir = tmp_path / "python-sdk"
    output_dir.mkdir()

    result = update_docs_json(
        docs_json,
        ["fastmcp.client"],
        output_dir,
        regenerate_all=True,
        anchor_name="Python SDK",
        mintlify_version="v999",
    )
    assert result is False
    captured = capsys.readouterr()
    assert "v999" in captured.out
    assert "v3.0.0" in captured.out  # should list available versions