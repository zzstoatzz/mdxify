"""Test stale file cleanup when using --all."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from mdxify.cli import main


def test_stale_files_removed_with_all_flag():
    """Test that stale MDX files are removed when using --all."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "docs"
        output_dir.mkdir()
        
        # Create some existing MDX files
        old_file = output_dir / "mymodule-old_name.mdx"
        old_file.write_text("# Old Module")
        keep_file = output_dir / "mymodule-keep.mdx"
        keep_file.write_text("# Keep Module")
        unrelated_file = output_dir / "other-module.mdx"
        unrelated_file.write_text("# Other Module")
        
        # Mock the modules to process
        modules_to_process = ["mymodule.keep", "mymodule.new_name"]
        
        # Mock the necessary functions
        with patch("mdxify.cli.find_all_modules") as mock_find_all:
            mock_find_all.return_value = modules_to_process
            
            with patch("mdxify.cli.parse_module_fast") as mock_parse:
                mock_parse.return_value = MagicMock()
                
                with patch("mdxify.cli.generate_mdx"):
                    with patch("mdxify.cli.get_module_source_file") as mock_source:
                        mock_source.return_value = Path("/fake/path.py")
                        
                        with patch("sys.argv", ["mdxify", "--all", "--root-module", "mymodule", 
                                               "--output-dir", str(output_dir), "--no-update-nav"]):
                            try:
                                main()
                            except SystemExit:
                                pass
        
        # Check that the old file was removed
        assert not old_file.exists(), "Old file should have been removed"
        # Keep file should still exist (would be regenerated)
        # Unrelated file should still exist (different root module)
        assert unrelated_file.exists(), "Unrelated file should not be removed"