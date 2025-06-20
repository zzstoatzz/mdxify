"""Tests for the navigation module."""


from mdxify.navigation import build_hierarchical_navigation


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