"""CLI interface for mdxify."""

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from ._version import __version__
from .discovery import find_all_modules, get_module_source_file, should_include_module
from .generator import generate_mdx
from .navigation import update_docs_json
from .parser import parse_module_fast, parse_modules_with_inheritance
from .renderers import get_renderer
from .source_links import detect_github_repo_url


class SimpleProgressBar:
    """A simple progress bar using only built-in Python."""
    
    def __init__(self, total: int, desc: str = "Processing"):
        self.total = total
        self.current = 0
        self.desc = desc
        self.start_time = time.time()
        self.lock = Lock()
        self._last_line_length = 0
        
    def update(self, n: int = 1):
        """Update progress by n steps."""
        with self.lock:
            self.current += n
            self._render()
    
    def _render(self):
        """Render the progress bar to stdout."""
        if self.total == 0:
            return
            
        # Calculate metrics
        pct = (self.current / self.total) * 100
        elapsed = time.time() - self.start_time
        rate = self.current / elapsed if elapsed > 0 else 0
        eta = (self.total - self.current) / rate if rate > 0 else 0
        
        # Build progress bar
        bar_width = 30
        filled = int(bar_width * self.current / self.total)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        # Format time
        def fmt_time(seconds):
            if seconds < 60:
                return f"{seconds:.3f}s"
            else:
                return f"{seconds/60:.3f}m"
        
        # Build output line
        line = f"\r{self.desc}: [{bar}] {self.current}/{self.total} ({pct:.0f}%) | {fmt_time(elapsed)} elapsed"
        if self.current < self.total:
            line += f" | ~{fmt_time(eta)} remaining"
        
        # Clear previous line if it was longer
        if len(line) < self._last_line_length:
            line += " " * (self._last_line_length - len(line))
        self._last_line_length = len(line)
        
        # Write to stdout
        sys.stdout.write(line)
        sys.stdout.flush()
    
    def finish(self):
        """Mark progress as complete."""
        with self.lock:
            self.current = self.total
            self._render()
            print()  # New line after progress bar


def remove_excluded_files(output_dir: Path, exclude_patterns: list[str], extension: str = "mdx") -> int:
    """Remove existing MDX files for excluded modules.
    
    Returns the number of files removed.
    """
    if not output_dir.exists():
        return 0
        
    removed_count = 0
    for mdx_file in output_dir.glob(f"*.{extension}"):
        # Convert filename back to module name
        stem = mdx_file.stem
        if stem.endswith("-__init__"):
            module_name = stem[:-9].replace("-", ".")
        else:
            module_name = stem.replace("-", ".")
        
        # Check if this module should be excluded
        for exclude_pattern in exclude_patterns:
            if module_name == exclude_pattern or module_name.startswith(exclude_pattern + "."):
                mdx_file.unlink()
                removed_count += 1
                break
                
    return removed_count


def main():
    parser = argparse.ArgumentParser(
        description="Generate API reference documentation for Python modules"
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"mdxify {__version__}"
    )
    parser.add_argument(
        "modules",
        nargs="*",
        help="Modules to document (e.g., prefect.flows prefect.tasks). If none specified, generates all.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate documentation for all modules under the root module",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="docs/python-sdk",
        help="Output directory for generated MDX files (default: docs/python-sdk)",
    )
    parser.add_argument(
        "--update-nav",
        action="store_true",
        default=True,
        help="Update docs.json navigation (default: True)",
    )
    parser.add_argument(
        "--no-update-nav",
        dest="update_nav",
        action="store_false",
        help="Skip updating docs.json navigation",
    )
    parser.add_argument(
        "--root-module",
        help="Root module to generate docs for (required when using --all)",
    )
    parser.add_argument(
        "--skip-empty-parents",
        action="store_true",
        default=False,
        help="Skip parent modules that only contain boilerplate (default: False)",
    )
    parser.add_argument(
        "--anchor-name",
        "--navigation-key",
        dest="navigation_key",
        default="SDK Reference",
        help="Name of the navigation anchor or group to update (default: 'SDK Reference')",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        help="Module to exclude from documentation (can be specified multiple times). Excludes the module and all its submodules.",
    )
    parser.add_argument(
        "--repo-url",
        help="GitHub repository URL for source code links (e.g., https://github.com/owner/repo). If not provided, will attempt to detect from git remote.",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Git branch name for source code links (default: main)",
    )
    parser.add_argument(
        "--format",
        choices=["mdx", "md"],
        default="mdx",
        help="Output format: 'mdx' (default) or 'md' (Markdown)",
    )
    parser.add_argument(
        "--include-internal",
        action="store_true",
        default=False,
        help="Include internal modules in the documentation (default: False)",
    )
    parser.add_argument(
        "--include-inheritance",
        action="store_true",
        default=False,
        help="Include inherited methods from parent classes in child class documentation (default: False)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Show verbose output including parsing warnings (default: False)",
    )

    args = parser.parse_args()

    # Show version banner for easier debugging and support requests
    print(f"mdxify version {__version__}")

    # Configure logging based on verbosity
    if args.verbose:
        # Show all warnings when verbose
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        # Suppress griffe warnings by default
        logging.getLogger('griffe').setLevel(logging.ERROR)
        # Also suppress other noisy loggers
        logging.getLogger('griffe.agents.visitor').setLevel(logging.ERROR)
        logging.getLogger('griffe.agents.inspector').setLevel(logging.ERROR)
        logging.getLogger('griffe.docstrings').setLevel(logging.ERROR)
        # Keep root logger at WARNING for important messages
        logging.basicConfig(level=logging.WARNING, format='%(message)s')

    # Validate arguments
    if args.all and not args.root_module:
        parser.error("--root-module is required when using --all")

    # Determine which modules to process
    modules_to_process = []

    if args.all:
        # Generate all modules under root
        if args.verbose:
            print(f"Finding all {args.root_module} modules...")
        modules_to_process = find_all_modules(args.root_module)
        if args.verbose:
            print(f"Found {len(modules_to_process)} modules")
        else:
            print(f"Found {len(modules_to_process)} {args.root_module} modules")
    elif not args.modules:
        parser.error("Either specify modules to document or use --all with --root-module")
    else:
        # Process specified modules and their submodules
        for module in args.modules:
            modules_to_process.append(module)
            # Also find submodules
            submodules = find_all_modules(module)
            modules_to_process.extend(submodules)

    # Remove duplicates
    modules_to_process = sorted(set(modules_to_process))
    
    # Select renderer early (used by cleanup for excludes)
    renderer = get_renderer(args.format)
    ext = renderer.file_extension

    # Filter out excluded modules
    if args.exclude:
        excluded_count = 0
        filtered_modules = []
        matched_patterns = set()
        
        for module in modules_to_process:
            # Check if this module or any parent module is excluded
            should_exclude = False
            for exclude_pattern in args.exclude:
                if module == exclude_pattern or module.startswith(exclude_pattern + "."):
                    should_exclude = True
                    excluded_count += 1
                    matched_patterns.add(exclude_pattern)
                    break
            if not should_exclude:
                filtered_modules.append(module)
        
        # Warn about patterns that didn't match anything
        unmatched_patterns = set(args.exclude) - matched_patterns
        for pattern in unmatched_patterns:
            print(f"Warning: --exclude pattern '{pattern}' did not match any modules")
        
        if excluded_count > 0 and args.verbose:
            print(f"Excluding {excluded_count} modules based on --exclude patterns")
        modules_to_process = filtered_modules
        
        # Remove existing MDX files for excluded modules (declarative behavior)
        removed_count = remove_excluded_files(args.output_dir, args.exclude, extension=ext)
        if removed_count > 0:
            print(f"Removed {removed_count} existing {ext} files for excluded modules")

    # Determine repository URL for source links
    repo_url = args.repo_url
    if not repo_url:
        repo_url = detect_github_repo_url()
        if repo_url and args.verbose:
            print(f"Detected repository: {repo_url}")

    # If using Markdown, disable nav updates (Mintlify is MDX-focused)
    if renderer.file_extension == "md" and args.update_nav:
        print("Warning: --format md selected; skipping navigation updates.")
        args.update_nav = False
    
    # Clean up existing MDX files when using --all (declarative behavior)
    if args.all and args.output_dir.exists():
        existing_files = list(args.output_dir.glob(f"*.{ext}"))
        # Build a set of expected filenames for current modules
        expected_files = set()
        for module_name in modules_to_process:
            # Check if this module has submodules
            has_submodules = any(
                m.startswith(module_name + ".")
                and m.count(".") == module_name.count(".") + 1
                for m in modules_to_process
            )
            if has_submodules:
                filename = f"{module_name.replace('.', '-')}-__init__.{ext}"
            else:
                filename = f"{module_name.replace('.', '-')}.{ext}"
            expected_files.add(filename)
        
        # Remove files that shouldn't exist anymore
        removed_count = 0
        for mdx_file in existing_files:
            if mdx_file.name not in expected_files:
                # Only remove files that match the root module pattern
                stem = mdx_file.stem
                if stem.endswith("-__init__"):
                    module_name = stem[:-9].replace("-", ".")
                else:
                    module_name = stem.replace("-", ".")
                
                # Check if this file belongs to the root module we're regenerating
                if args.root_module and module_name.startswith(args.root_module):
                    mdx_file.unlink()
                    removed_count += 1
        
        if removed_count > 0:
            print(f"Removed {removed_count} stale {ext} files")
    
    # Generate documentation
    generated_modules = []
    failed_modules = []
    updated_count = 0
    created_count = 0

    start_time = time.time()

    if args.include_inheritance:
        # Use inheritance-aware parsing
        try:
            module_results = parse_modules_with_inheritance(modules_to_process, args.include_internal)
            
            for module_name, module_info in module_results.items():
                try:
                    # Check if this module has submodules
                    has_submodules = any(
                        m.startswith(module_name + ".")
                        and m.count(".") == module_name.count(".") + 1
                        for m in modules_to_process
                    )

                    # If it has submodules, save it as __init__
                    if has_submodules:
                        output_file = (
                            args.output_dir / f"{module_name.replace('.', '-')}-__init__.{ext}"
                        )
                    else:
                        output_file = args.output_dir / f"{module_name.replace('.', '-')}.{ext}"

                    generate_mdx(
                        module_info, 
                        output_file,
                        repo_url=repo_url,
                        branch=args.branch,
                        root_module=args.root_module,
                        renderer=renderer,
                    )

                    generated_modules.append(module_name)
                    if args.verbose:
                        print(f"Processing {module_name}... done (with inheritance)")
                except Exception as e:
                    failed_modules.append((module_name, str(e)))
                    if args.verbose:
                        print(f"Processing {module_name}... failed: {e}")
                    else:
                        print(f"✗ {module_name}")
                    
        except Exception as e:
            print(f"Failed to parse modules with inheritance: {e}")
            # Fall back to regular parsing
            print("Falling back to regular parsing...")
            args.include_inheritance = False

    else:
        def process_module(module_data):
            """Process a single module."""
            i, module_name, include_internal, verbose = module_data
            
            # Skip internal modules
            if not should_include_module(module_name, include_internal):
                msg = f"[{i}/{len(modules_to_process)}] Skipping {module_name} (internal module)" if verbose else None
                return (msg, None, None, "skipped", False)

            source_file = get_module_source_file(module_name)
            if not source_file:
                msg = f"[{i}/{len(modules_to_process)}] Skipping {module_name} (no source file)" if verbose else None
                return (msg, None, None, "skipped", False)

            try:
                module_start = time.time()

                module_info = parse_module_fast(module_name, source_file, include_internal)

                # Check if this module has submodules
                has_submodules = any(
                    m.startswith(module_name + ".")
                    and m.count(".") == module_name.count(".") + 1
                    for m in modules_to_process
                )

                # If it has submodules, save it as __init__
                if has_submodules:
                    output_file = (
                        args.output_dir / f"{module_name.replace('.', '-')}-__init__.{ext}"
                    )
                else:
                    output_file = args.output_dir / f"{module_name.replace('.', '-')}.{ext}"

                file_existed = output_file.exists()
                generate_mdx(
                    module_info, 
                    output_file,
                    repo_url=repo_url,
                    branch=args.branch,
                    root_module=args.root_module,
                    renderer=renderer,
                )

                module_time = time.time() - module_start
                if verbose:
                    msg = f"[{i}/{len(modules_to_process)}] Processing {module_name}... done ({module_time:.3f}s)"
                else:
                    msg = f"Processing {module_name}... done"
                return (msg, module_name, None, "success", file_existed)
            except Exception as e:
                if verbose:
                    msg = f"[{i}/{len(modules_to_process)}] Processing {module_name}... failed: {e}"
                else:
                    msg = f"✗ {module_name}"
                return (msg, None, (module_name, str(e)), "failed", False)

        # Process modules in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Submit all tasks
            future_to_module = {
                executor.submit(process_module, (i, module_name, args.include_internal, args.verbose)): module_name
                for i, module_name in enumerate(modules_to_process, 1)
            }
            
            # Count existing files to determine the action
            existing_files = 0
            if args.output_dir.exists():
                for module_name in modules_to_process:
                    has_submodules = any(
                        m.startswith(module_name + ".")
                        and m.count(".") == module_name.count(".") + 1
                        for m in modules_to_process
                    )
                    if has_submodules:
                        output_file = args.output_dir / f"{module_name.replace('.', '-')}-__init__.{ext}"
                    else:
                        output_file = args.output_dir / f"{module_name.replace('.', '-')}.{ext}"
                    if output_file.exists():
                        existing_files += 1
            
            # Choose description based on whether we're updating or creating
            if existing_files == len(modules_to_process):
                desc = "Updating docs"
            elif existing_files > 0:
                desc = "Processing docs"
            else:
                desc = "Generating docs"
            
            # Create progress bar if not in verbose mode
            progress_bar = None if args.verbose else SimpleProgressBar(
                total=len(modules_to_process),
                desc=desc
            )
            
            # Process results as they complete
            for future in as_completed(future_to_module):
                message, success_module, failed_module, status, file_existed = future.result()
                
                if args.verbose:
                    if message:
                        print(message)
                else:
                    # Update progress bar
                    if progress_bar:
                        progress_bar.update()
                
                if success_module:
                    generated_modules.append(success_module)
                    if file_existed:
                        updated_count += 1
                    else:
                        created_count += 1
                if failed_module:
                    failed_modules.append(failed_module)
            
            # Finish progress bar
            if progress_bar:
                progress_bar.finish()

    total_time = time.time() - start_time

    # Update navigation if requested
    if args.update_nav and generated_modules:
        docs_json_path = Path("docs/docs.json")
        if docs_json_path.exists():
            if args.verbose:
                print("\nUpdating docs.json navigation...")
            # Only do complete regeneration when --all is used
            regenerate_all = args.all or (not args.modules)
            success = update_docs_json(
                docs_json_path, 
                generated_modules, 
                args.output_dir,
                regenerate_all=regenerate_all,
                skip_empty_parents=args.skip_empty_parents,
                anchor_name=args.navigation_key
            )
            if not success:
                print("Failed to update navigation")
        else:
            print(f"\nWarning: Could not find {docs_json_path}")

    # Summary
    if not args.verbose:
        # Concise summary
        if created_count == 0 and updated_count > 0:
            print(f"\n✓ Updated {updated_count} modules in {total_time:.3f}s")
        elif created_count > 0 and updated_count > 0:
            print(f"\n✓ Created {created_count} and updated {updated_count} modules in {total_time:.3f}s")
        else:
            print(f"\n✓ Generated {len(generated_modules)} modules in {total_time:.3f}s")
        if failed_modules:
            print(f"✗ Failed: {len(failed_modules)} modules")
    else:
        # Verbose summary
        print("\nGeneration complete!")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Generated: {len(generated_modules)} modules")
        print(f"  Failed: {len(failed_modules)} modules")
        if modules_to_process:
            print(f"  Average time per module: {total_time / len(modules_to_process):.3f}s")

    if failed_modules:
        print("\nFailed modules:")
        for module, error in failed_modules[:10]:  # Show first 10
            print(f"  - {module}: {error}")
        if len(failed_modules) > 10:
            print(f"  ... and {len(failed_modules) - 10} more")

    sys.exit(1 if failed_modules else 0)


if __name__ == "__main__":
    main()
