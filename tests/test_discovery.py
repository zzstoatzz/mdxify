"""Tests for the discovery module."""



from mdxify.discovery import should_include_module


def test_should_include_module_excludes_private():
    """Test that private modules are excluded."""
    assert should_include_module("prefect.flows") is True
    assert should_include_module("prefect._internal") is False
    assert should_include_module("prefect.flows._private") is False


def test_should_include_module_excludes_known_patterns():
    """Test that known internal patterns are excluded."""
    assert should_include_module("prefect.testing.fixtures") is False
    assert should_include_module("prefect.agent.something") is False
    assert should_include_module("prefect.blocks.core") is True