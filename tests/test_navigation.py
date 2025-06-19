"""Tests for the navigation module."""


from mdxify.navigation import build_hierarchical_navigation


def test_build_hierarchical_navigation_simple():
    """Test building navigation for simple module structure."""
    modules = [
        "prefect.flows",
        "prefect.tasks",
        "prefect.blocks.core",
        "prefect.blocks.system",
    ]
    
    result = build_hierarchical_navigation(modules, skip_empty_parents=False)
    
    # Should have two top-level entries
    assert len(result) == 3
    
    # Find the blocks group
    blocks_group = None
    for item in result:
        if isinstance(item, dict) and item.get("group") == "blocks":
            blocks_group = item
            break
    
    assert blocks_group is not None
    assert len(blocks_group["pages"]) >= 2  # core and system


def test_build_hierarchical_navigation_nested():
    """Test building navigation for deeply nested modules."""
    modules = [
        "prefect.foo",
        "prefect.foo.bar",
        "prefect.foo.bar.baz",
        "prefect.foo.qux",
    ]
    
    result = build_hierarchical_navigation(modules, skip_empty_parents=False)
    
    # Should have one top-level group for 'foo'
    assert len(result) == 1
    assert result[0]["group"] == "foo"
    
    # Check nested structure
    # The parent module should have pages (submodules)
    assert "pages" in result[0]
    assert len(result[0]["pages"]) > 0