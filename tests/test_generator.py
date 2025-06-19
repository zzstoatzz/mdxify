"""Tests for the generator module."""



from mdxify.generator import generate_mdx, is_module_empty


def test_is_module_empty_detects_empty_content(tmp_path):
    """Test that empty module detection works."""
    mdx_file = tmp_path / "test.mdx"
    mdx_file.write_text("""
---
title: test
---

# `test.module`

*This module is empty or contains only private/internal implementations.*
""")
    
    assert is_module_empty(mdx_file) is True


def test_is_module_empty_detects_non_empty(tmp_path):
    """Test that non-empty modules are detected correctly."""
    mdx_file = tmp_path / "test.mdx"
    mdx_file.write_text("""
---
title: test
---

# `test.module`

This module has content.

## Functions

### `example`
""")
    
    assert is_module_empty(mdx_file) is False


def test_generate_mdx_empty_module(tmp_path):
    """Test generating MDX for an empty module."""
    module_info = {
        "name": "test.empty",
        "docstring": "",
        "functions": [],
        "classes": [],
        "source_file": "/path/to/file.py"
    }
    
    output_file = tmp_path / "test-empty.mdx"
    generate_mdx(module_info, output_file)
    
    content = output_file.read_text()
    assert "title: empty" in content
    assert "*This module is empty or contains only private/internal implementations.*" in content


def test_generate_mdx_with_content(tmp_path):
    """Test generating MDX for a module with content."""
    module_info = {
        "name": "test.example",
        "docstring": "This is a test module.",
        "functions": [
            {
                "name": "test_function",
                "signature": "test_function(x: int) -> str",
                "docstring": "A test function.",
                "line": 10
            }
        ],
        "classes": [
            {
                "name": "TestClass",
                "docstring": "A test class.",
                "methods": [
                    {
                        "name": "test_method",
                        "signature": "test_method(self)",
                        "docstring": "A test method.",
                        "line": 20
                    }
                ],
                "line": 15
            }
        ],
        "source_file": "/path/to/file.py"
    }
    
    output_file = tmp_path / "test-example.mdx"
    generate_mdx(module_info, output_file)
    
    content = output_file.read_text()
    
    # Check frontmatter
    assert "title: example" in content
    assert "sidebarTitle: example" in content
    
    # Check module header
    assert "# `test.example`" in content
    assert "This is a test module." in content
    
    # Check functions section
    assert "## Functions" in content
    assert "### `test_function`" in content
    assert "test_function(x: int) -> str" in content
    assert "A test function." in content
    
    # Check classes section
    assert "## Classes" in content
    assert "### `TestClass`" in content
    assert "A test class." in content
    assert "#### `test_method`" in content
    assert "test_method(self)" in content