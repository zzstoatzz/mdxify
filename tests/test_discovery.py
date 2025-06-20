"""Tests for the discovery module."""



from mdxify.discovery import should_include_module


def test_should_include_module_excludes_private():
    """Test that private modules are excluded."""
    assert should_include_module("mypackage.flows") is True
    assert should_include_module("mypackage._internal") is False
    assert should_include_module("mypackage.flows._private") is False


def test_should_include_module_excludes_known_patterns():
    """Test that known internal patterns are excluded."""
    assert should_include_module("mypackage.testing.fixtures") is False
    assert should_include_module("mypackage.tests.test_something") is False
    assert should_include_module("mypackage.blocks.core") is True