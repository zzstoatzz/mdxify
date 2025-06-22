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
    # Note: they should be sorted, so order is: plain pages first, then groups
    assert len(result) == 3
    
    # Find the blocks group
    blocks_group = None
    for item in result:
        if isinstance(item, dict) and item.get("group") == "mypackage.blocks":
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
    
    # Check group names (now with fully qualified names)
    group_names = {item["group"] for item in result}
    assert "mypackage.utils" in group_names
    assert "mypackage.models" in group_names


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
    result = update_docs_json(docs_json, [], output_dir)
    
    # Should return False and print warning
    assert result is False
    captured = capsys.readouterr()
    assert "Could not find mdxify anchor 'SDK Reference' or placeholder" in captured.out
    assert '{"$mdxify": "generated"}' in captured.out


def test_navigation_uses_output_dir_prefix(tmp_path):
    """Test that navigation entries use the correct output directory prefix."""
    # The navigation prefix is calculated in update_docs_json, not build_hierarchical_navigation
    # build_hierarchical_navigation returns just the filenames without path prefix
    modules = [
        "mypackage.core",
        "mypackage.utils.helpers",
        "mypackage.utils.validators",
    ]
    
    output_dir = tmp_path / "python-sdk"
    result = build_hierarchical_navigation(modules, output_dir, skip_empty_parents=False)
    
    # Check top-level module (without prefix)
    assert any(item == "mypackage-core" for item in result)
    
    # Check nested modules in group
    utils_group = None
    for item in result:
        if isinstance(item, dict) and item.get("group") == "mypackage.utils":
            utils_group = item
            break
    
    assert utils_group is not None
    assert "mypackage-utils-helpers" in utils_group["pages"]
    assert "mypackage-utils-validators" in utils_group["pages"]


def test_update_docs_json_with_custom_output_path(tmp_path):
    """Test that update_docs_json correctly adds path prefix for custom output directories."""
    # Create a docs.json with placeholder
    docs_json = tmp_path / "docs.json"
    docs_config = {
        "navigation": [{"anchor": "SDK Reference", "pages": [{"$mdxify": "generated"}]}]
    }
    
    with open(docs_json, "w") as f:
        json.dump(docs_config, f)
    
    # Create output dir as python-sdk instead of api
    output_dir = tmp_path / "python-sdk"
    output_dir.mkdir()
    
    # Create some dummy MDX files
    (output_dir / "mypackage-core.mdx").write_text("# Core")
    (output_dir / "mypackage-utils-helpers.mdx").write_text("# Helpers")
    
    # Update docs.json
    generated_modules = ["mypackage.core", "mypackage.utils.helpers"]
    update_docs_json(docs_json, generated_modules, output_dir, regenerate_all=True)
    
    # Check the result
    with open(docs_json) as f:
        updated_config = json.load(f)
    
    pages = updated_config["navigation"][0]["pages"]
    # Should have entries with python-sdk prefix
    assert any("python-sdk/mypackage-core" in str(page) for page in pages)
    
    # Find the utils group and check its pages have the prefix too
    utils_group = None
    for item in pages:
        if isinstance(item, dict) and item.get("group") == "mypackage.utils":
            utils_group = item
            break
    
    assert utils_group is not None
    assert any("python-sdk/mypackage-utils-helpers" in page for page in utils_group["pages"])


def test_navigation_path_calculation(tmp_path):
    """Test that navigation paths are calculated correctly relative to docs root."""
    # Test when output is under docs/
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    output_dir = docs_dir / "python-sdk"
    output_dir.mkdir()
    
    # Create dummy MDX files
    (output_dir / "mypackage-core.mdx").write_text("# Core")
    
    # Create docs.json
    docs_json = docs_dir / "docs.json"
    docs_config = {
        "navigation": [{"anchor": "SDK Reference", "pages": [{"$mdxify": "generated"}]}]
    }
    
    with open(docs_json, "w") as f:
        json.dump(docs_config, f)
    
    # Update navigation
    update_docs_json(docs_json, ["mypackage.core"], output_dir, regenerate_all=True)
    
    # Check result
    with open(docs_json) as f:
        result = json.load(f)
    
    pages = result["navigation"][0]["pages"]
    print(f"Navigation pages (under docs): {pages}")
    assert "python-sdk/mypackage-core" in pages
    
    # Test when output is NOT under docs/
    external_dir = tmp_path / "external-docs"
    external_dir.mkdir()
    (external_dir / "mypackage-api.mdx").write_text("# API")
    
    # Reset docs.json
    docs_config["navigation"][0]["pages"] = [{"$mdxify": "generated"}]
    with open(docs_json, "w") as f:
        json.dump(docs_config, f)
    
    # Update with external dir
    update_docs_json(docs_json, ["mypackage.api"], external_dir, regenerate_all=True)
    
    with open(docs_json) as f:
        result = json.load(f)
    
    # Should just have filename without path prefix when outside docs/
    pages = result["navigation"][0]["pages"]
    assert "mypackage-api" in pages
    assert "external-docs/mypackage-api" not in str(pages)


def test_navigation_sorting(tmp_path):
    """Test that navigation entries are sorted consistently."""
    modules = [
        "zebra",
        "alpha",
        "beta.sub1",
        "beta.sub2", 
        "charlie",
    ]
    
    result = build_hierarchical_navigation(modules, tmp_path, skip_empty_parents=False)
    
    # Extract top-level names
    top_level_names = []
    for item in result:
        if isinstance(item, str):
            # Extract module name from filename
            name = item.replace("-", ".").replace(".mdx", "")
            top_level_names.append(name)
        elif isinstance(item, dict) and "group" in item:
            top_level_names.append(item["group"])
    
    # Should be sorted: plain pages first (alpha, charlie, zebra), then groups (beta)
    expected_order = ["alpha", "charlie", "zebra", "beta"]
    assert top_level_names == expected_order


def test_update_mintlify_format_anchor(tmp_path):
    """Test updating an existing anchor in Mintlify format (navigation.anchors)."""
    # Create a docs.json with Mintlify format
    docs_json = tmp_path / "docs.json"
    docs_config = {
        "name": "Test Project",
        "navigation": {
            "anchors": [
                {
                    "anchor": "Getting Started",
                    "pages": ["intro", "quickstart"]
                },
                {
                    "anchor": "SDK Reference",
                    "icon": "code",
                    "pages": [
                        "python-sdk/old-module"  # Existing entry
                    ]
                }
            ]
        }
    }
    
    with open(docs_json, "w") as f:
        json.dump(docs_config, f)
    
    # Create some new MDX files
    output_dir = tmp_path / "python-sdk"
    output_dir.mkdir()
    (output_dir / "mypackage-core.mdx").write_text("# Core")
    (output_dir / "mypackage-utils.mdx").write_text("# Utils")
    
    # Update docs.json
    generated_modules = ["mypackage.core", "mypackage.utils"]
    result = update_docs_json(docs_json, generated_modules, output_dir, regenerate_all=True)
    
    # Should succeed
    assert result is True
    
    # Check the result
    with open(docs_json) as f:
        updated_config = json.load(f)
    
    # Should have replaced the old pages with new ones
    pages = updated_config["navigation"]["anchors"][1]["pages"]
    assert len(pages) == 2
    assert "python-sdk/mypackage-core" in pages
    assert "python-sdk/mypackage-utils" in pages
    assert "python-sdk/old-module" not in pages  # Old entry should be gone
    # Icon should be preserved
    assert updated_config["navigation"]["anchors"][1]["icon"] == "code"


def test_hierarchical_navigation_with_fully_qualified_names(tmp_path):
    """Test that top-level groups use fully qualified names, but nested groups don't."""
    modules = [
        "fastmcp.cli",
        "fastmcp.cli.run",
        "fastmcp.server.auth",
        "fastmcp.server.auth.providers.bearer",
    ]
    
    output_dir = tmp_path / "api"
    result = build_hierarchical_navigation(modules, output_dir, skip_empty_parents=False)
    
    # Find the CLI group
    cli_group = None
    for item in result:
        if isinstance(item, dict) and item.get("group", "").endswith("cli"):
            cli_group = item
            break
    
    assert cli_group is not None
    assert cli_group["group"] == "fastmcp.cli"  # Top-level should be fully qualified
    
    # Find the server group
    server_group = None
    for item in result:
        if isinstance(item, dict) and item.get("group", "").endswith("server"):
            server_group = item
            break
    
    assert server_group is not None
    assert server_group["group"] == "fastmcp.server"  # Top-level should be fully qualified
    
    # Check for nested auth group
    auth_group = None
    for page in server_group["pages"]:
        if isinstance(page, dict) and "auth" in page.get("group", ""):
            auth_group = page
            break
    
    assert auth_group is not None
    assert auth_group["group"] == "auth"  # Nested group should NOT be fully qualified
    
    # Check for deeply nested providers group
    providers_group = None
    for page in auth_group["pages"]:
        if isinstance(page, dict) and "providers" in page.get("group", ""):
            providers_group = page
            break
    
    assert providers_group is not None
    assert providers_group["group"] == "providers"  # Deeply nested should also not be fully qualified


def test_update_docs_json_with_tabs_structure(tmp_path):
    """Test updating docs.json when anchor is nested within tabs."""
    # Create a docs.json with tabs structure like FastMCP uses
    docs_json = tmp_path / "docs.json"
    docs_config = {
        "name": "FastMCP",
        "navigation": {
            "tabs": [
                {
                    "tab": "Documentation",
                    "anchors": [
                        {
                            "anchor": "Documentation",
                            "pages": ["getting-started/welcome"]
                        },
                        {
                            "anchor": "Community",
                            "pages": ["community/showcase"]
                        }
                    ]
                },
                {
                    "tab": "SDK Reference",
                    "anchors": [
                        {
                            "anchor": "Python SDK",
                            "icon": "python",
                            "pages": [
                                {"$mdxify": "generated"}
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    with open(docs_json, "w") as f:
        json.dump(docs_config, f)
    
    # Create some MDX files
    output_dir = tmp_path / "python-sdk"
    output_dir.mkdir()
    (output_dir / "fastmcp-client.mdx").write_text("# Client")
    (output_dir / "fastmcp-server.mdx").write_text("# Server")
    
    # Update docs.json
    generated_modules = ["fastmcp.client", "fastmcp.server"]
    result = update_docs_json(
        docs_json, 
        generated_modules, 
        output_dir, 
        regenerate_all=True,
        anchor_name="Python SDK"
    )
    
    # Should succeed
    assert result is True
    
    # Check the result
    with open(docs_json) as f:
        updated_config = json.load(f)
    
    # Navigate to the SDK pages
    sdk_tab = updated_config["navigation"]["tabs"][1]
    assert sdk_tab["tab"] == "SDK Reference"
    
    python_sdk_anchor = sdk_tab["anchors"][0]
    assert python_sdk_anchor["anchor"] == "Python SDK"
    assert python_sdk_anchor["icon"] == "python"  # Should preserve icon
    
    pages = python_sdk_anchor["pages"]
    assert len(pages) == 2
    assert "python-sdk/fastmcp-client" in pages
    assert "python-sdk/fastmcp-server" in pages