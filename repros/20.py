#!/usr/bin/env python
import os
import statistics
import subprocess
import time
from pathlib import Path

# Ensure we're running from mdxify root
os.chdir(Path(__file__).parent.parent)

def run_benchmark(command: list[str], runs: int = 5) -> dict:
    """Run a command multiple times and measure performance."""
    times = []
    for i in range(runs):
        start = time.perf_counter()
        result = subprocess.run(command, capture_output=True, text=True)
        end = time.perf_counter()
        elapsed = end - start
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.3f}s")
        if result.returncode != 0:
            print(f"  Error: {result.stderr}")
    
    return {
        "min": min(times),
        "max": max(times),
        "mean": statistics.mean(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "times": times
    }

def main():
    print("=== mdxify Performance Benchmark ===\n")
    
    # Test on Prefect (matching the issue)
    prefect_path = Path("sandbox/prefect")
    if prefect_path.exists():
        print("Testing on Prefect codebase (290 modules as per issue #20)\n")
        
        print("1. Testing with uvx (simulating Prefect's current usage):")
        cmd_uvx = [
            "uvx", "--with-editable", ".", "--refresh-package", "mdxify",
            "mdxify", "--all", "--root-module", "prefect", 
            "--output-dir", str(prefect_path / "docs/v3/api-ref/python"),
            "--anchor-name", "Python SDK Reference",
            "--exclude", "prefect.agent",
            "--include-inheritance",
            "--repo-url", "https://github.com/PrefectHQ/prefect"
        ]
        print("Command: uvx ... mdxify --all --root-module prefect ...")
        results_uvx = run_benchmark(cmd_uvx, runs=3)
        print(f"  Average: {results_uvx['mean']:.3f}s ± {results_uvx['stdev']:.3f}s\n")
        
        print("2. Testing with uvx without --refresh-package:")
        cmd_uvx_no_refresh = [
            "uvx", "--with-editable", ".", 
            "mdxify", "--all", "--root-module", "prefect",
            "--output-dir", str(prefect_path / "docs/v3/api-ref/python"),
            "--anchor-name", "Python SDK Reference",
            "--exclude", "prefect.agent",
            "--include-inheritance",
            "--repo-url", "https://github.com/PrefectHQ/prefect"
        ]
        print("Command: uvx --with-editable . mdxify ...")
        results_no_refresh = run_benchmark(cmd_uvx_no_refresh, runs=3)
        print(f"  Average: {results_no_refresh['mean']:.3f}s ± {results_no_refresh['stdev']:.3f}s\n")
        
        print("3. Testing with uv run (direct execution):")
        cmd_uv = [
            "uv", "run", "mdxify", "--all", "--root-module", "prefect",
            "--output-dir", str(prefect_path / "docs/v3/api-ref/python"),
            "--anchor-name", "Python SDK Reference",
            "--exclude", "prefect.agent",
            "--include-inheritance",
            "--repo-url", "https://github.com/PrefectHQ/prefect"
        ]
        print("Command: uv run mdxify ...")
        results_uv = run_benchmark(cmd_uv, runs=3)
        print(f"  Average: {results_uv['mean']:.3f}s ± {results_uv['stdev']:.3f}s\n")
        
        print("4. Testing import time only:")
        import_test = [
            "uv", "run", "python", "-c", 
            "import time; s=time.perf_counter(); from mdxify.cli import app; print(f'Import time: {time.perf_counter()-s:.3f}s')"
        ]
        print("Testing CLI import time...")
        subprocess.run(import_test)
        
        print("\n=== Summary ===")
        print(f"uvx with --refresh-package: {results_uvx['mean']:.3f}s")
        print(f"uvx without refresh: {results_no_refresh['mean']:.3f}s")
        print(f"uv run (direct): {results_uv['mean']:.3f}s")
        print(f"Overhead from --refresh-package: {results_uvx['mean'] - results_no_refresh['mean']:.3f}s")
        print(f"Overhead from uvx vs uv run: {results_no_refresh['mean'] - results_uv['mean']:.3f}s")
    else:
        print("Prefect test directory not found. Please ensure sandbox/prefect exists.")

if __name__ == "__main__":
    main()