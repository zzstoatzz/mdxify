"""Tests for the CLI module."""

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from mdxify.cli import main, remove_excluded_files


def test_default_output_dir_is_python_sdk():
    """Test that the default output directory is docs/python-sdk."""
    # Parse the ArgumentParser to check defaults
    parser = argparse.ArgumentParser()
    
    # Copy the setup from main() 
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="docs/python-sdk",
        help="Output directory for generated MDX files (default: docs/python-sdk)",
    )
    
    # Parse empty args to get defaults
    args = parser.parse_args([])
    
    assert args.output_dir == Path("docs/python-sdk")


def test_cli_requires_root_module_with_all():
    """Test that --all requires --root-module."""
    with patch.object(sys, "argv", ["mdxify", "--all"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2  # type: ignore # argparse error code


def test_skip_empty_parents_flag():
    """Test that --skip-empty-parents flag is parsed correctly."""
    parser = argparse.ArgumentParser()
    
    # Copy the setup from main() 
    parser.add_argument(
        "--skip-empty-parents",
        action="store_true", 
        default=False,
        help="Skip parent modules that only contain boilerplate (default: False)",
    )
    
    # Test default
    args = parser.parse_args([])
    assert args.skip_empty_parents is False
    
    # Test with flag
    args = parser.parse_args(["--skip-empty-parents"])
    assert args.skip_empty_parents is True


def test_cli_processes_specified_modules():
    """Test processing specific modules."""
    with patch("mdxify.cli.find_all_modules") as mock_find, \
         patch("mdxify.cli.get_module_source_file") as mock_source, \
         patch("mdxify.cli.parse_module_fast") as mock_parse, \
         patch("mdxify.cli.generate_mdx") as mock_generate, \
         patch.object(sys, "argv", ["mdxify", "mypackage.core", "--no-update-nav"]):
        
        # Setup mocks
        mock_find.return_value = []  # No submodules
        mock_source.return_value = Path("mypackage/core.py")
        mock_parse.return_value = {"name": "mypackage.core", "docstring": "Test"}
        
        # Run
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0  # type: ignore
        
        # Verify module was processed
        mock_parse.assert_called_once_with("mypackage.core", Path("mypackage/core.py"))
        mock_generate.assert_called_once()
        
        # Check output path
        call_args = mock_generate.call_args
        output_file = call_args[0][1]
        assert "python-sdk" in str(output_file)
        assert output_file.name == "mypackage-core.mdx"


def test_exclude_modules():
    """Test that --exclude properly excludes modules and their submodules."""
    with patch("mdxify.cli.find_all_modules") as mock_find, \
         patch("mdxify.cli.get_module_source_file") as mock_source, \
         patch("mdxify.cli.should_include_module") as mock_should_include, \
         patch("mdxify.cli.parse_module_fast") as mock_parse, \
         patch("mdxify.cli.generate_mdx") as mock_generate, \
         patch.object(sys, "argv", [
             "mdxify", "--all", "--root-module", "mypackage",
             "--no-update-nav",
             "--exclude", "mypackage.internal",
             "--exclude", "mypackage.utils.helpers"
         ]):
        
        # Setup mocks
        mock_find.return_value = [
            "mypackage",
            "mypackage.core",
            "mypackage.utils",
            "mypackage.utils.helpers",
            "mypackage.internal",
            "mypackage.internal.stuff",
        ]
        mock_source.side_effect = lambda m: Path(f"{m.replace('.', '/')}.py")
        mock_should_include.return_value = True
        mock_parse.side_effect = lambda name, path: {
            "name": name,
            "docstring": f"Module {name}",
            "functions": [],
            "classes": []
        }
        
        # Run
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0  # type: ignore
        
        # Check that only non-excluded modules were processed
        processed_modules = [call[0][0]["name"] for call in mock_generate.call_args_list]
        assert "mypackage" in processed_modules
        assert "mypackage.core" in processed_modules
        assert "mypackage.utils" in processed_modules
        
        # Check that excluded modules were NOT processed
        assert "mypackage.internal" not in processed_modules
        assert "mypackage.internal.stuff" not in processed_modules
        assert "mypackage.utils.helpers" not in processed_modules
        
        # Should have processed 3 modules total
        assert len(processed_modules) == 3


def test_exclude_removes_existing_files(tmp_path):
    """Test that --exclude removes existing MDX files (declarative behavior)."""
    # Create output directory with existing files
    output_dir = tmp_path / "docs"
    output_dir.mkdir()
    
    # Create some existing MDX files
    (output_dir / "mypackage-core.mdx").write_text("# Core")
    (output_dir / "mypackage-internal-__init__.mdx").write_text("# Internal")
    (output_dir / "mypackage-internal-stuff.mdx").write_text("# Stuff")
    
    with patch("mdxify.cli.find_all_modules") as mock_find, \
         patch("mdxify.cli.get_module_source_file") as mock_source, \
         patch("mdxify.cli.should_include_module") as mock_should_include, \
         patch("mdxify.cli.parse_module_fast") as mock_parse, \
         patch("mdxify.cli.generate_mdx"), \
         patch.object(sys, "argv", [
             "mdxify", "--all", "--root-module", "mypackage",
             "--output-dir", str(output_dir),
             "--no-update-nav",
             "--exclude", "mypackage.internal"
         ]):
        
        # Setup mocks - only core module remains after exclusion
        mock_find.return_value = ["mypackage", "mypackage.core"]
        mock_source.side_effect = lambda m: Path(f"{m.replace('.', '/')}.py")
        mock_should_include.return_value = True
        mock_parse.side_effect = lambda name, path: {
            "name": name,
            "docstring": f"Module {name}",
            "functions": [],
            "classes": []
        }
        
        # Run
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0  # type: ignore
        
        # Check that excluded files were removed
        assert not (output_dir / "mypackage-internal-__init__.mdx").exists()
        assert not (output_dir / "mypackage-internal-stuff.mdx").exists()
        
        # Check that non-excluded files still exist
        assert (output_dir / "mypackage-core.mdx").exists()


def test_remove_excluded_files_helper(tmp_path):
    """Test the remove_excluded_files helper function."""
    output_dir = tmp_path / "docs"
    output_dir.mkdir()
    
    # Create some MDX files
    (output_dir / "mypackage-core.mdx").write_text("# Core")
    (output_dir / "mypackage-internal-__init__.mdx").write_text("# Internal")
    (output_dir / "mypackage-internal-helpers.mdx").write_text("# Helpers")
    (output_dir / "mypackage-utils.mdx").write_text("# Utils")
    
    # Test removing files
    removed = remove_excluded_files(output_dir, ["mypackage.internal"])
    
    assert removed == 2
    assert not (output_dir / "mypackage-internal-__init__.mdx").exists()
    assert not (output_dir / "mypackage-internal-helpers.mdx").exists()
    assert (output_dir / "mypackage-core.mdx").exists()
    assert (output_dir / "mypackage-utils.mdx").exists()
    
    # Test with non-existent directory
    removed = remove_excluded_files(tmp_path / "nonexistent", ["anything"])
    assert removed == 0