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
    """Test relative path extraction."""
    # Test src layout
    path = Path("/home/user/project/src/mypackage/module.py")
    result = get_relative_path(path, "mypackage")
    assert result == Path("src/mypackage/module.py")
    
    # Test flat layout
    path = Path("/home/user/project/mypackage/module.py")
    result = get_relative_path(path, "mypackage")
    assert result == Path("mypackage/module.py")
    
    # Test no match
    path = Path("/home/user/project/other/module.py")
    result = get_relative_path(path, "mypackage")
    assert result is None


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
    expected = '### `function_name` <sup><a href="https://github.com/owner/repo/blob/main/module.py#L42" target="_blank"><Icon icon="github" style="width: 14px; height: 14px;" /></a></sup>'
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
    expected = '### `function_name` <sup><a href="https://github.com/owner/repo/blob/main/module.py#L42" target="_blank"><Icon icon="github" style="width: 14px; height: 14px;" /></a></sup>'
    assert result == expected


def test_inherited_method_source_links():
    """Test that inherited methods get source links pointing to their parent class."""
    import tempfile
    from textwrap import dedent

    from mdxify.generator import generate_mdx
    from mdxify.parser import parse_modules_with_inheritance
    
    # Create test files with realistic repository structure
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create src/test/ directory structure
        src_path = tmp_path / "src" / "test"
        src_path.mkdir(parents=True, exist_ok=True)
        
        # Create parent module
        parent_file = src_path / "parent_module.py"
        parent_file.write_text(dedent('''
            """Parent module."""
            
            class BaseClass:
                """A base class with methods."""
                
                def base_method(self, x: int) -> int:
                    """A method from the base class."""
                    return x * 2
        '''))
        
        # Create child module
        child_file = src_path / "child_module.py"
        child_file.write_text(dedent('''
            """Child module."""
            
            from .parent_module import BaseClass
            
            class ChildClass(BaseClass):
                """A child class that inherits from BaseClass."""
                
                def child_method(self, value: str) -> str:
                    """A method specific to the child class."""
                    return f"Child: {value}"
        '''))
        
        # Mock module discovery
        import sys
        sys.path.insert(0, str(src_path))
        
        try:
            from unittest.mock import patch
            
            def mock_get_module_source_file(module_name):
                if module_name == "parent_module":
                    return parent_file
                elif module_name == "child_module":
                    return child_file
                return None
            
            def mock_find_all_modules(root_module):
                return ["parent_module", "child_module"]
            
            with patch('mdxify.discovery.get_module_source_file', side_effect=mock_get_module_source_file), \
                 patch('mdxify.discovery.find_all_modules', side_effect=mock_find_all_modules):
                
                # Parse with inheritance
                results = parse_modules_with_inheritance(["child_module"])
                child_result = results["child_module"]
                
                # Generate MDX with source links
                output_file = tmp_path / "test.mdx"
                
                generate_mdx(
                    child_result,
                    output_file,
                    repo_url="https://github.com/test/repo",
                    branch="main",
                    root_module="test",
                )
                
                # Read the generated MDX
                mdx_content = output_file.read_text()
                
                # Check that the inherited method has a source link
                # The source link should point to the parent module
                assert "base_method" in mdx_content
                assert "parent_module.py" in mdx_content
                assert "github.com/test/repo" in mdx_content
                
                # Check that the child method also has a source link
                assert "child_method" in mdx_content
                assert "child_module.py" in mdx_content
                
        finally:
            sys.path.remove(str(src_path))
