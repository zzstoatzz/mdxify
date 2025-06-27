"""Tests for source code link generation."""

from pathlib import Path

from mdxify.source_links import (
    add_source_link_to_header,
    detect_github_repo_url,
    generate_source_link,
    get_relative_path,
)


def test_detect_github_repo_url(monkeypatch):
    """Test GitHub repository URL detection."""
    # This test will pass if we're in a git repo with GitHub remote
    # In CI or non-git environments, it might return None
    result = detect_github_repo_url()
    assert result is None or result.startswith("https://github.com/")


def test_get_relative_path():
    """Test getting relative paths from source files."""
    # Test src layout
    assert get_relative_path(
        Path("/home/user/project/src/mypackage/module.py"), "mypackage"
    ) == Path("src/mypackage/module.py")
    
    # Test flat layout
    assert get_relative_path(
        Path("/home/user/project/mypackage/module.py"), "mypackage"
    ) == Path("mypackage/module.py")
    
    # Test nested modules
    assert get_relative_path(
        Path("/home/user/project/src/mypackage/submodule/file.py"), "mypackage"
    ) == Path("src/mypackage/submodule/file.py")


def test_generate_source_link():
    """Test source link generation."""
    # Basic test
    link = generate_source_link(
        "https://github.com/owner/repo",
        "main",
        Path("/home/user/project/src/mypackage/module.py"),
        42,
        "mypackage",
    )
    assert link == "https://github.com/owner/repo/blob/main/src/mypackage/module.py#L42"
    
    # Test with different branch
    link = generate_source_link(
        "https://github.com/owner/repo",
        "develop",
        Path("/home/user/project/mypackage/module.py"),
        100,
        "mypackage",
    )
    assert link == "https://github.com/owner/repo/blob/develop/mypackage/module.py#L100"
    
    # Test with trailing slash in repo URL
    link = generate_source_link(
        "https://github.com/owner/repo/",
        "main",
        Path("/home/user/project/src/mypackage/module.py"),
        1,
        "mypackage",
    )
    assert link == "https://github.com/owner/repo/blob/main/src/mypackage/module.py#L1"


def test_add_source_link_to_header():
    """Test adding source links to markdown headers."""
    # Test with link
    result = add_source_link_to_header(
        "### `function_name`",
        "https://github.com/owner/repo/blob/main/module.py#L42",
    )
    # The link should be inline with GitHub icon
    expected = '### `function_name` <sup><a href="https://github.com/owner/repo/blob/main/module.py#L42" target="_blank"><Icon icon="github" size="14" /></a></sup>'
    assert result == expected
    
    # Test that link is inline
    assert '<sup><a href="' in result
    
    # Test with no link
    result = add_source_link_to_header("### `function_name`", None)
    assert result == "### `function_name`"


def test_add_source_link_with_custom_text(monkeypatch):
    """Test source link with icon (env var no longer used)."""
    # The environment variable is no longer used since we use icon
    # But let's test that it still works without errors
    monkeypatch.setenv("MDXIFY_SOURCE_LINK_TEXT", "[src]")
    result = add_source_link_to_header(
        "### `function_name`",
        "https://github.com/owner/repo/blob/main/module.py#L42",
    )
    # Should still produce the icon, not the custom text
    expected = '### `function_name` <sup><a href="https://github.com/owner/repo/blob/main/module.py#L42" target="_blank"><Icon icon="github" size="14" /></a></sup>'
    assert result == expected