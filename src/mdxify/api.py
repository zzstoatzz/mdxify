"""Programmatic API for mdxify.

This module provides a Python API for generating MDX documentation without CLI overhead.
This is the recommended approach for CI/CD and pre-commit scenarios where performance matters.
"""

from pathlib import Path


def generate_docs(
    root_module: str,
    output_dir: str | Path = "docs/python-sdk",
    *,
    exclude: list[str] | None = None,
    anchor_name: str = "SDK Reference",
    repo_url: str | None = None,
    branch: str = "main",
    include_internal: bool = False,
    include_inheritance: bool = False,
    skip_empty_parents: bool = False,
    verbose: bool = False,
) -> dict:
    """Generate MDX documentation for a Python package.
    
    This is the programmatic API for mdxify, designed for optimal performance
    when called from Python scripts (e.g., in CI/CD pipelines).
    
    Args:
        root_module: The root module to document (e.g., 'prefect')
        output_dir: Output directory for MDX files
        exclude: List of module patterns to exclude
        anchor_name: Navigation anchor name in docs.json
        repo_url: GitHub repository URL for source links
        branch: Git branch for source links
        include_internal: Include internal/private modules
        include_inheritance: Include inherited methods in docs
        skip_empty_parents: Skip parent modules with only boilerplate
        verbose: Enable verbose output
        
    Returns:
        Dictionary with generation statistics:
        - modules_processed: Number of modules processed
        - modules_failed: Number of modules that failed
        - time_elapsed: Total time in seconds
        - files_created: Number of new files created
        - files_updated: Number of existing files updated
        
    Example:
        >>> from mdxify.api import generate_docs
        >>> result = generate_docs(
        ...     "mypackage",
        ...     output_dir="docs/api",
        ...     exclude=["mypackage.internal"],
        ... )
        >>> print(f"Generated {result['modules_processed']} modules")
    """
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Lazy imports to reduce startup time
    from .discovery import (
        find_all_modules,
        get_module_source_file,
        should_include_module,
    )
    from .generator import generate_mdx
    from .navigation import update_docs_json
    from .parser import parse_module_fast, parse_modules_with_inheritance
    from .source_links import detect_github_repo_url
    
    start_time = time.time()
    output_dir_path = Path(output_dir)
    exclude = exclude or []
    
    # Find all modules
    modules_to_process = find_all_modules(root_module)
    
    # Filter excluded modules
    if exclude:
        filtered = []
        for module in modules_to_process:
            if not any(
                module == pattern or module.startswith(pattern + ".")
                for pattern in exclude
            ):
                filtered.append(module)
        modules_to_process = filtered
    
    # Detect repo URL if not provided
    if not repo_url:
        repo_url = detect_github_repo_url()
    
    # Process modules
    generated_modules = []
    failed_modules = []
    created_count = 0
    updated_count = 0
    
    if include_inheritance:
        # Batch processing with inheritance
        module_results = parse_modules_with_inheritance(modules_to_process, include_internal)
        for module_name, module_info in module_results.items():
            try:
                has_submodules = any(
                    m.startswith(module_name + ".")
                    and m.count(".") == module_name.count(".") + 1
                    for m in modules_to_process
                )
                
                if has_submodules:
                    output_file = output_dir_path / f"{module_name.replace('.', '-')}-__init__.mdx"
                else:
                    output_file = output_dir_path / f"{module_name.replace('.', '-')}.mdx"
                
                file_existed = output_file.exists()
                generate_mdx(module_info, output_file, repo_url=repo_url, branch=branch, root_module=root_module)
                
                generated_modules.append(module_name)
                if file_existed:
                    updated_count += 1
                else:
                    created_count += 1
            except Exception as e:
                failed_modules.append((module_name, str(e)))
    else:
        # Parallel processing without inheritance
        def process_module(module_name):
            if not should_include_module(module_name, include_internal):
                return None, None, "skipped"
            
            source_file = get_module_source_file(module_name)
            if not source_file:
                return None, None, "no_source"
            
            try:
                module_info = parse_module_fast(module_name, source_file, include_internal)
                
                has_submodules = any(
                    m.startswith(module_name + ".")
                    and m.count(".") == module_name.count(".") + 1
                    for m in modules_to_process
                )
                
                if has_submodules:
                    output_file = output_dir_path / f"{module_name.replace('.', '-')}-__init__.mdx"
                else:
                    output_file = output_dir_path / f"{module_name.replace('.', '-')}.mdx"
                
                file_existed = output_file.exists()
                generate_mdx(module_info, output_file, repo_url=repo_url, branch=branch, root_module=root_module)
                
                return module_name, None, ("created" if not file_existed else "updated")
            except Exception as e:
                return None, (module_name, str(e)), "failed"
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(process_module, m): m for m in modules_to_process}
            
            for future in as_completed(futures):
                success, failure, status = future.result()
                if success:
                    generated_modules.append(success)
                    if status == "created":
                        created_count += 1
                    elif status == "updated":
                        updated_count += 1
                if failure:
                    failed_modules.append(failure)
    
    # Update navigation
    docs_json_path = Path("docs/docs.json")
    if docs_json_path.exists() and generated_modules:
        update_docs_json(
            docs_json_path,
            generated_modules,
            output_dir_path,
            regenerate_all=True,
            skip_empty_parents=skip_empty_parents,
            anchor_name=anchor_name,
        )
    
    elapsed = time.time() - start_time
    
    return {
        "modules_processed": len(generated_modules),
        "modules_failed": len(failed_modules),
        "time_elapsed": elapsed,
        "files_created": created_count,
        "files_updated": updated_count,
        "failed_modules": failed_modules if verbose else [],
    }