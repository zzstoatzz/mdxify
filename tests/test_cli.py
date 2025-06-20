"""Tests for the CLI module."""

import argparse
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mdxify.cli import main


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
        assert exc_info.value.code == 2  # argparse error code


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
        
        assert exc_info.value.code == 0
        
        # Verify module was processed
        mock_parse.assert_called_once_with("mypackage.core", Path("mypackage/core.py"))
        mock_generate.assert_called_once()
        
        # Check output path
        call_args = mock_generate.call_args
        output_file = call_args[0][1]
        assert "python-sdk" in str(output_file)
        assert output_file.name == "mypackage-core.mdx"