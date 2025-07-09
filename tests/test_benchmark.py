"""Benchmark tests for mdxify performance."""

import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.fixture
def test_package(tmp_path):
    """Create a test package with many modules for benchmarking."""
    package_dir = tmp_path / "testpkg"
    package_dir.mkdir()
    
    # Create __init__.py
    (package_dir / "__init__.py").write_text('"""Test package."""')
    
    # Create multiple modules with various content
    for i in range(10):
        module_content = f'''"""Module {i} documentation.

This is a test module with various components.
"""

from typing import List, Optional, Union


class TestClass{i}:
    """Test class {i}.
    
    This class demonstrates various features.
    
    Attributes:
        value: The stored value
        name: The name of the instance
    """
    
    def __init__(self, value: int, name: str = "default"):
        """Initialize the test class.
        
        Args:
            value: The initial value
            name: The name of the instance
        """
        self.value = value
        self.name = name
    
    def process(self, data: List[str]) -> List[str]:
        """Process the data.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed data
            
        Raises:
            ValueError: If data is empty
        """
        if not data:
            raise ValueError("Data cannot be empty")
        return [f"{{self.name}}: {{item}}" for item in data]
    
    def calculate(self, x: float, y: float) -> float:
        """Calculate result from inputs.
        
        Args:
            x: First number
            y: Second number
            
        Returns:
            The calculation result
        """
        return x * y * self.value


def function{i}(arg1: str, arg2: int = 10) -> Optional[str]:
    """Test function {i}.
    
    Args:
        arg1: The first argument
        arg2: The second argument with default
        
    Returns:
        The processed string or None
    """
    if arg2 > 0:
        return f"{{arg1}} * {{arg2}}"
    return None


def complex_function{i}(
    data: List[Union[str, int]], 
    *args: str, 
    flag: bool = False,
    **kwargs: Any
) -> dict:
    """Complex function with various argument types.
    
    Args:
        data: Mixed type data list
        *args: Variable positional arguments
        flag: Boolean flag
        **kwargs: Keyword arguments
        
    Returns:
        Dictionary with processed results
    """
    return {{
        "data": data,
        "args": args,
        "flag": flag,
        "kwargs": kwargs
    }}
'''
        (package_dir / f"module{i}.py").write_text(module_content)
    
    # Create some submodules
    subpkg = package_dir / "subpackage"
    subpkg.mkdir()
    (subpkg / "__init__.py").write_text('"""Subpackage."""')
    
    for i in range(5):
        (subpkg / f"submodule{i}.py").write_text(f'''"""Submodule {i}."""

def sub_function{i}():
    """Function in submodule."""
    pass
''')
    
    return package_dir


def run_mdxify_benchmark(package_path: Path, output_dir: Path, iterations: int = 3) -> dict:
    """Run mdxify and measure performance."""
    times = []
    
    for _ in range(iterations):
        # Clear output directory
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)
        
        start_time = time.time()
        
        # Run mdxify
        cmd = [
            sys.executable, "-m", "mdxify",
            "--all",
            "--root-module", package_path.name,
            "--output-dir", str(output_dir),
            "--no-update-nav"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(package_path.parent),
            capture_output=True,
            text=True
        )
        
        end_time = time.time()
        
        if result.returncode == 0:
            times.append(end_time - start_time)
    
    return {
        "times": times,
        "average": sum(times) / len(times) if times else 0,
        "min": min(times) if times else 0,
        "max": max(times) if times else 0,
    }


def test_benchmark_performance(test_package, tmp_path):
    """Benchmark mdxify performance."""
    output_dir = tmp_path / "output"
    
    results = run_mdxify_benchmark(test_package, output_dir, iterations=3)
    
    print("\nBenchmark Results:")
    print(f"  Average: {results['average']:.3f}s")
    print(f"  Min: {results['min']:.3f}s")
    print(f"  Max: {results['max']:.3f}s")
    
    # Count generated files
    mdx_files = list(output_dir.rglob("*.mdx"))
    print(f"  Files generated: {len(mdx_files)}")
    
    # Set a baseline - should process ~15 modules in under 0.5 seconds
    assert results['average'] < 0.5, f"Performance regression: {results['average']:.3f}s average"


@pytest.mark.parametrize("module_count", [50, 100])
def test_benchmark_scale(tmp_path, module_count):
    """Test performance at different scales."""
    package_dir = tmp_path / "largepkg"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text('"""Large package."""')
    
    # Create many simple modules
    for i in range(module_count):
        (package_dir / f"module{i}.py").write_text(f'''"""Module {i}."""

def function{i}():
    """Simple function."""
    pass
''')
    
    output_dir = tmp_path / "output"
    results = run_mdxify_benchmark(package_dir, output_dir, iterations=1)
    
    print(f"\nScale test ({module_count} modules): {results['average']:.3f}s")
    print(f"  Per module: {results['average']/module_count*1000:.1f}ms")
    
    # Should process at least 100 modules per second
    assert results['average'] < module_count / 100