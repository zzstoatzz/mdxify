"""End-to-end tests for mdxify functionality."""

import json
import subprocess
import sys
from textwrap import dedent

import pytest


@pytest.fixture
def test_package(tmp_path):
    """Create a minimal test package structure."""
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    
    # Create __init__.py
    (pkg_dir / "__init__.py").write_text('"""My package."""')
    
    # Create a module with docstring
    (pkg_dir / "core.py").write_text(dedent('''
        """Core functionality module."""
        
        def process(data: str) -> str:
            """Process the input data.
            
            Args:
                data: The data to process
                
            Returns:
                The processed data
            """
            return data.upper()
    '''))
    
    # Create a submodule
    utils_dir = pkg_dir / "utils"
    utils_dir.mkdir()
    (utils_dir / "__init__.py").write_text('"""Utilities module."""')
    
    (utils_dir / "helpers.py").write_text(dedent('''
        """Helper functions."""
        
        def format_output(text: str, width: int = 80) -> str:
            """Format text to specified width.
            
            Args:
                text: Text to format
                width: Maximum line width
                
            Returns:
                Formatted text
            """
            return text[:width]
    '''))
    
    # Add the test package to Python path
    sys.path.insert(0, str(tmp_path))
    yield pkg_dir
    sys.path.remove(str(tmp_path))


def test_cli_default_output_directory(test_package, tmp_path):
    """Test that CLI uses docs/python-sdk as default output directory."""
    # Run mdxify on the test package
    result = subprocess.run(
        [sys.executable, "-m", "mdxify", "mypkg.core", "--no-update-nav"],
        cwd=tmp_path,
        capture_output=True,
        text=True
    )
    
    # Debug output if failed
    if result.returncode != 0:
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
    
    assert result.returncode == 0, f"mdxify failed: {result.stderr}"
    
    # Check that file was created in docs/python-sdk
    expected_file = tmp_path / "docs" / "python-sdk" / "mypkg-core.mdx"
    assert expected_file.exists(), f"Expected file not found: {expected_file}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    
    # Verify content
    content = expected_file.read_text()
    assert "Core functionality module" in content
    assert "process" in content


def test_cli_custom_output_directory(test_package, tmp_path):
    """Test using a custom output directory."""
    custom_dir = tmp_path / "custom-docs"
    
    result = subprocess.run(
        [sys.executable, "-m", "mdxify", "mypkg.core", 
         "--output-dir", str(custom_dir), "--no-update-nav"],
        cwd=tmp_path,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    expected_file = custom_dir / "mypkg-core.mdx"
    assert expected_file.exists()


def test_navigation_with_python_sdk_prefix(test_package, tmp_path):
    """Test that navigation entries include the python-sdk prefix."""
    # Create docs.json with placeholder
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    docs_json = docs_dir / "docs.json"
    
    docs_config = {
        "navigation": {
            "anchors": [
                {
                    "anchor": "SDK Reference",
                    "pages": [{"$mdxify": "generated"}]
                }
            ]
        }
    }
    
    docs_json.write_text(json.dumps(docs_config, indent=2))
    
    # Run mdxify with navigation update
    result = subprocess.run(
        [sys.executable, "-m", "mdxify", "--all", "--root-module", "mypkg"],
        cwd=tmp_path,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"mdxify failed: {result.stderr}"
    
    # Check navigation was updated correctly
    with open(docs_json) as f:
        updated_config = json.load(f)
    
    pages = updated_config["navigation"]["anchors"][0]["pages"]
    
    # Should have entries with python-sdk prefix
    assert any("python-sdk/mypkg-core" in str(page) for page in pages)
    
    # Check for utils group with fully qualified name
    utils_group = None
    for item in pages:
        if isinstance(item, dict) and item.get("group") == "mypkg.utils":
            utils_group = item
            break
    
    assert utils_group is not None, "Should have mypkg.utils group"
    assert any("python-sdk/mypkg-utils-helpers" in page for page in utils_group["pages"])




def test_module_with_submodules_generates_init_file(test_package, tmp_path):
    """Test that modules with submodules get __init__ suffix."""
    result = subprocess.run(
        [sys.executable, "-m", "mdxify", "--all", "--root-module", "mypkg", 
         "--no-update-nav"],
        cwd=tmp_path,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Failed: {result.stderr}"
    
    output_dir = tmp_path / "docs" / "python-sdk"
    
    # List what was actually created
    if output_dir.exists():
        files = list(output_dir.glob("*.mdx"))
        print(f"Generated files: {[f.name for f in files]}")
    
    # mypkg.utils has submodules, so should have __init__ suffix
    assert (output_dir / "mypkg-utils-__init__.mdx").exists()
    
    # Leaf modules should not have __init__ suffix
    assert (output_dir / "mypkg-core.mdx").exists()
    assert not (output_dir / "mypkg-core-__init__.mdx").exists()


def test_fully_qualified_group_names(test_package, tmp_path):
    """Test that top-level navigation groups use fully qualified module names."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    docs_json = docs_dir / "docs.json"
    
    docs_config = {
        "navigation": {
            "anchors": [
                {
                    "anchor": "SDK Reference",
                    "pages": [{"$mdxify": "generated"}]
                }
            ]
        }
    }
    
    docs_json.write_text(json.dumps(docs_config, indent=2))
    
    # Generate docs for nested structure
    result = subprocess.run(
        [sys.executable, "-m", "mdxify", "--all", "--root-module", "mypkg"],
        cwd=tmp_path,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    
    with open(docs_json) as f:
        updated_config = json.load(f)
    
    # Find the utils group
    pages = updated_config["navigation"]["anchors"][0]["pages"]
    utils_group = None
    for item in pages:
        if isinstance(item, dict) and "utils" in item.get("group", ""):
            utils_group = item
            break
    
    assert utils_group is not None
    # Top-level group name should be fully qualified
    assert utils_group["group"] == "mypkg.utils"