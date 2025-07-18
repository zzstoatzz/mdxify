"""Utilities for generating source code links."""

import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


def detect_github_repo_url() -> Optional[str]:
    """Detect GitHub repository URL from git remote."""
    try:
        # Get the remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote_url = result.stdout.strip()
        
        # Convert SSH URLs to HTTPS
        if remote_url.startswith("git@github.com:"):
            # git@github.com:owner/repo.git -> https://github.com/owner/repo
            remote_url = remote_url.replace("git@github.com:", "https://github.com/")
        
        # Remove .git suffix if present
        if remote_url.endswith(".git"):
            remote_url = remote_url[:-4]
        
        # Validate it's a GitHub URL
        parsed = urlparse(remote_url)
        if parsed.netloc == "github.com" and len(parsed.path.strip("/").split("/")) == 2:
            return remote_url
            
    except subprocess.CalledProcessError:
        pass
    
    return None


def get_relative_path(file_path: Path, root_module: str) -> Optional[Path]:
    """Get the relative path from the repository root to the source file.
    
    Args:
        file_path: Absolute path to the source file
        root_module: The root module name (e.g., 'prefect', 'fastmcp')
    
    Returns:
        Relative path from repo root, or None if unable to determine
    """
    # Convert to Path object and string for manipulation
    file_path = Path(file_path)
    path_str = str(file_path)
    
    # Look for the module in the path
    # Handle both src layout (/src/module/) and flat layout (/module/)
    src_pattern = f"/src/{root_module}/"
    flat_pattern = f"/{root_module}/"
    
    if src_pattern in path_str:
        # src layout: find where /src/module/ starts
        idx = path_str.find(src_pattern)
        # Go back to include 'src' in the relative path
        relative_start = idx + 1  # +1 to skip the leading '/'
        return Path(path_str[relative_start:])
    elif flat_pattern in path_str:
        # flat layout: find where /module/ starts
        idx = path_str.rfind(flat_pattern)  # Use rfind to get the last occurrence
        # Go back to include just the module name
        relative_start = idx + 1  # +1 to skip the leading '/'
        return Path(path_str[relative_start:])
    
    return None


def generate_source_link(
    repo_url: str,
    branch: str,
    file_path: Path,
    line_number: int,
    root_module: Optional[str] = None,
) -> Optional[str]:
    """Generate a GitHub source code link.
    
    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/owner/repo)
        branch: Git branch name
        file_path: Path to the source file
        line_number: Line number in the source file
        root_module: Root module name for finding relative paths
    
    Returns:
        GitHub URL to the specific line, or None if unable to generate
    """
    if not repo_url:
        return None
    
    # Ensure repo_url doesn't end with slash
    repo_url = repo_url.rstrip("/")
    
    # Get relative path
    if root_module:
        relative_path = get_relative_path(file_path, root_module)
    else:
        # Fallback: try to detect from file path
        # This is less reliable but might work for simple cases
        relative_path = None
        path_parts = Path(file_path).parts
        for i, part in enumerate(path_parts):
            if part in ["src", "lib"]:
                relative_path = Path(*path_parts[i:])
                break
    
    if not relative_path:
        return None
    
    # Convert to forward slashes for URL
    path_str = str(relative_path).replace("\\", "/")
    
    # Generate GitHub URL
    return f"{repo_url}/blob/{branch}/{path_str}#L{line_number}"


def add_source_link_to_header(
    header: str,
    source_link: Optional[str],
    link_text: str = "[source]",
) -> str:
    """Add a source link to a markdown header.
    
    Args:
        header: The markdown header (e.g., "### `function_name`")
        source_link: The source code URL
        link_text: Text for the link (default: "[source]")
    
    Returns:
        Header with inline source link icon
    """
    if not source_link:
        return header
    
    # Add GitHub icon inline with the header
    # Using Mintlify's Icon component with proper CSS units for Firefox compatibility
    github_icon = f' <sup><a href="{source_link}" target="_blank"><Icon icon="github" style="width: 14px; height: 14px;" /></a></sup>'
    
    # Return header with inline GitHub icon
    return f"{header}{github_icon}"