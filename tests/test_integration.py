"""Integration tests for mdxify with real projects."""

import os
import platform
import subprocess
import tempfile
from pathlib import Path

import pytest


def run_command(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, and stderr."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env or os.environ.copy(),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.fixture()
def setup_test_env():
    """Set up a temporary directory with a test environment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        yield tmpdir


class TestPrefectIntegration:
    """Test mdxify with Prefect project structure."""
    
    @pytest.fixture()
    def prefect_mock(self, setup_test_env):
        """Create a mock Prefect-like structure."""
        base_dir = setup_test_env / "prefect_test"
        base_dir.mkdir()
        
        # Create a minimal Prefect-like structure
        src_dir = base_dir / "src" / "prefect"
        src_dir.mkdir(parents=True)
        
        # Create __init__.py
        (src_dir / "__init__.py").write_text('''"""Prefect orchestration framework."""
__version__ = "3.0.0"
''')
        
        # Create flows module
        flows_dir = src_dir / "flows"
        flows_dir.mkdir()
        (flows_dir / "__init__.py").write_text('''"""Prefect flows."""

from .flow import Flow

__all__ = ["Flow"]
''')
        
        (flows_dir / "flow.py").write_text('''"""Flow implementation."""
from typing import Any


class Flow:
    """A Prefect flow.
    
    Flows are the primary unit of orchestration in Prefect.
    """
    
    def __init__(self, name: str = None):
        """Initialize a flow.
        
        Args:
            name: The name of the flow.
        """
        self.name = name or "unnamed"
    
    def run(self) -> Any:
        """Run the flow."""
        return {"status": "success"}
''')
        
        # Create tasks module
        tasks_dir = src_dir / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "__init__.py").write_text('''"""Prefect tasks."""

from .task import task

__all__ = ["task"]
''')
        
        (tasks_dir / "task.py").write_text('''"""Task implementation."""
from typing import Callable


def task(fn: Callable) -> Callable:
    """Decorator to create a Prefect task.
    
    Args:
        fn: The function to decorate.
    
    Returns:
        The decorated function.
    """
    return fn
''')
        
        # Create pyproject.toml
        (base_dir / "pyproject.toml").write_text('''[project]
name = "prefect"
version = "3.0.0"

[tool.setuptools]
packages = ["prefect"]

[tool.setuptools.package-dir]
"" = "src"
''')
        
        return base_dir
    
    def test_prefect_docs_generation_uvx_style(self, prefect_mock):
        """Test generating Prefect docs using uvx style (tool installation)."""
        output_dir = prefect_mock / "docs" / "api-ref"
        output_dir.mkdir(parents=True)
        
        # Install the mock project
        code, _, stderr = run_command(
            ["uv", "pip", "install", "-e", str(prefect_mock)],
            cwd=prefect_mock
        )
        assert code == 0, f"Failed to install mock project: {stderr}"
        
        # Run mdxify from source
        mdxify_root = Path(__file__).parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(mdxify_root / "src") + ":" + env.get("PYTHONPATH", "")
        
        code, stdout, stderr = run_command(
            [
                "python", "-m", "mdxify",
                "--all",
                "--root-module", "prefect",
                "--output-dir", str(output_dir),
                "--no-update-nav"
            ],
            cwd=prefect_mock,
            env=env
        )
        
        # Should succeed
        assert code == 0, f"mdxify failed: {stderr}\nOutput: {stdout}"
        
        # Check that files were generated
        generated_files = list(output_dir.glob("*.mdx"))
        assert len(generated_files) > 0, f"No files generated. Output: {stdout}\nFiles in dir: {list(output_dir.iterdir())}"
        
        # Check for specific expected files
        file_names = {f.name for f in generated_files}
        assert "prefect-flows-__init__.mdx" in file_names or "prefect-flows.mdx" in file_names
        assert "prefect-tasks-__init__.mdx" in file_names or "prefect-tasks.mdx" in file_names
        
        # Verify content of one of the generated files
        # Look for the actual flow.py module file (not __init__)
        flow_file = output_dir / "prefect-flows-flow.mdx"
        if flow_file.exists():
            flow_content = flow_file.read_text()
            assert "Flow" in flow_content  # Class name should be present
            assert "Flows are the primary unit" in flow_content  # Docstring should be present
        else:
            # Just verify files were generated
            assert len(generated_files) >= 3, f"Expected at least 3 files, got {len(generated_files)}"
    
    def test_prefect_docs_no_cleanup_when_no_modules_found(self, prefect_mock):
        """Test that existing docs are not deleted when modules can't be found."""
        output_dir = prefect_mock / "docs" / "api-ref"
        output_dir.mkdir(parents=True)
        
        # Create some existing documentation files
        existing_files = [
            output_dir / "prefect-flows.mdx",
            output_dir / "prefect-tasks.mdx",
            output_dir / "prefect-blocks.mdx",
        ]
        
        for f in existing_files:
            f.write_text(f"# Existing content for {f.name}")
        
        # Run mdxify without the package installed (simulating tool environment)
        mdxify_root = Path(__file__).parent.parent
        env = os.environ.copy()
        # Clear Python path to simulate isolated tool environment
        env["PYTHONPATH"] = str(mdxify_root / "src")
        
        code, stdout, stderr = run_command(
            [
                "python", "-m", "mdxify",
                "--all",
                "--root-module", "prefect",
                "--output-dir", str(output_dir),
                "--no-update-nav"
            ],
            cwd=prefect_mock,
            env=env
        )
        
        # Should exit with error
        assert code == 1
        assert "Could not find any modules" in stdout
        
        # All existing files should still exist
        for f in existing_files:
            assert f.exists(), f"{f} was incorrectly deleted"
            assert f.read_text() == f"# Existing content for {f.name}"


class TestFastMCPIntegration:
    """Test mdxify with FastMCP project structure."""
    
    @pytest.fixture()
    def fastmcp_mock(self, setup_test_env):
        """Create a mock FastMCP-like structure."""
        base_dir = setup_test_env / "fastmcp_test"
        base_dir.mkdir()
        
        # Create src/fastmcp structure
        src_dir = base_dir / "src" / "fastmcp"
        src_dir.mkdir(parents=True)
        
        # Create __init__.py
        (src_dir / "__init__.py").write_text('''"""FastMCP - Model Context Protocol."""
__version__ = "0.1.0"

from .server import FastMCP

__all__ = ["FastMCP"]
''')
        
        # Create server module
        server_dir = src_dir / "server"
        server_dir.mkdir()
        (server_dir / "__init__.py").write_text('''"""FastMCP server."""

from .server import FastMCP

__all__ = ["FastMCP"]
''')
        
        (server_dir / "server.py").write_text('''"""Server implementation."""
from typing import Any, Dict


class FastMCP:
    """FastMCP server.
    
    A Python implementation of the Model Context Protocol.
    """
    
    def __init__(self, name: str = "fastmcp"):
        """Initialize server.
        
        Args:
            name: Server name.
        """
        self.name = name
        self.tools: Dict[str, Any] = {}
    
    def tool(self, func):
        """Register a tool.
        
        Args:
            func: Function to register as a tool.
        
        Returns:
            The decorated function.
        """
        self.tools[func.__name__] = func
        return func
''')
        
        # Create client module
        client_dir = src_dir / "client"
        client_dir.mkdir()
        (client_dir / "__init__.py").write_text('''"""FastMCP client."""

from .client import MCPClient

__all__ = ["MCPClient"]
''')
        
        (client_dir / "client.py").write_text('''"""Client implementation."""


class MCPClient:
    """MCP client for connecting to servers.
    
    Provides a simple interface for MCP communication.
    """
    
    def __init__(self, url: str):
        """Initialize client.
        
        Args:
            url: Server URL.
        """
        self.url = url
    
    async def connect(self):
        """Connect to the server."""
        pass
''')
        
        # Create pyproject.toml
        (base_dir / "pyproject.toml").write_text('''[project]
name = "fastmcp"
version = "0.1.0"

[tool.setuptools]
packages = ["fastmcp"]

[tool.setuptools.package-dir]
"" = "src"
''')
        
        return base_dir
    
    def test_fastmcp_docs_generation(self, fastmcp_mock):
        """Test generating FastMCP docs."""
        output_dir = fastmcp_mock / "docs" / "python-sdk"
        output_dir.mkdir(parents=True)
        
        # Install the mock project
        code, _, stderr = run_command(
            ["uv", "pip", "install", "-e", str(fastmcp_mock)],
            cwd=fastmcp_mock
        )
        assert code == 0, f"Failed to install mock project: {stderr}"
        
        # Run mdxify from source
        mdxify_root = Path(__file__).parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(mdxify_root / "src") + ":" + env.get("PYTHONPATH", "")
        
        code, stdout, stderr = run_command(
            [
                "python", "-m", "mdxify",
                "--all",
                "--root-module", "fastmcp",
                "--output-dir", str(output_dir),
                "--no-update-nav",
                "--format", "md"  # FastMCP might use Markdown
            ],
            cwd=fastmcp_mock,
            env=env
        )
        
        # Should succeed
        assert code == 0, f"mdxify failed: {stderr}\nOutput: {stdout}"
        
        # Check that files were generated
        generated_files = list(output_dir.glob("*.md"))
        assert len(generated_files) > 0, f"No files generated. Output: {stdout}\nFiles in dir: {list(output_dir.iterdir())}"
        
        # Check for specific expected files
        file_names = {f.name for f in generated_files}
        assert "fastmcp-server-__init__.md" in file_names or "fastmcp-server.md" in file_names
        assert "fastmcp-client-__init__.md" in file_names or "fastmcp-client.md" in file_names
        
        # Verify content of one of the generated files
        # Look for the actual server.py module file (not __init__)
        server_file = output_dir / "fastmcp-server-server.md"
        if server_file.exists():
            server_content = server_file.read_text()
            assert "FastMCP" in server_content  # Class name should be present
            assert "Model Context Protocol" in server_content  # Docstring should be present
        else:
            # Just verify files were generated
            assert len(generated_files) >= 4, f"Expected at least 4 files, got {len(generated_files)}"


@pytest.mark.parametrize("system", [
    pytest.param("linux", marks=pytest.mark.skipif(
        platform.system() != "Linux", 
        reason="Linux-only test"
    )),
    pytest.param("darwin", marks=pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS-only test"
    )),
])
class TestCrossPlatform:
    """Test mdxify behavior across different platforms."""
    
    def test_platform_specific_behavior(self, system, setup_test_env):
        """Test that mdxify works consistently on the current platform."""
        # Create a simple test module
        test_dir = setup_test_env / "platform_test"
        test_dir.mkdir()
        
        src_dir = test_dir / "src" / "testmod"
        src_dir.mkdir(parents=True)
        
        (src_dir / "__init__.py").write_text('''"""Test module."""

def platform_func():
    """A platform-independent function."""
    return "hello"
''')
        
        (test_dir / "pyproject.toml").write_text('''[project]
name = "testmod"
version = "0.1.0"
''')
        
        # Install the test module
        code, _, _ = run_command(
            ["uv", "pip", "install", "-e", str(test_dir)],
            cwd=test_dir
        )
        assert code == 0
        
        # Run mdxify
        output_dir = test_dir / "docs"
        output_dir.mkdir()
        
        mdxify_root = Path(__file__).parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(mdxify_root / "src") + ":" + env.get("PYTHONPATH", "")
        
        code, stdout, stderr = run_command(
            [
                "python", "-m", "mdxify",
                "testmod",
                "--output-dir", str(output_dir),
                "--no-update-nav"
            ],
            cwd=test_dir,
            env=env
        )
        
        assert code == 0, f"Platform test failed on {system}: {stderr}"
        assert (output_dir / "testmod.mdx").exists()
        
        content = (output_dir / "testmod.mdx").read_text()
        assert "platform_func" in content