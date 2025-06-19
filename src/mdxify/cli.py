"""CLI interface for mdxify."""

import argparse
import sys
import time
from pathlib import Path

from .discovery import find_all_modules, get_module_source_file, should_include_module
from .generator import generate_mdx
from .navigation import update_docs_json
from .parser import parse_module_fast


def main():
    parser = argparse.ArgumentParser(
        description="Generate API reference documentation for Python modules"
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
        default="docs/v3/api-ref",
        help="Output directory for generated MDX files",
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
        default="prefect",
        help="Root module to generate docs for (default: prefect)",
    )

    args = parser.parse_args()

    # Determine which modules to process
    modules_to_process = []

    if args.all or (not args.modules):
        # Generate all modules under root
        print(f"Finding all {args.root_module} modules...")
        modules_to_process = find_all_modules(args.root_module)
        print(f"Found {len(modules_to_process)} modules")
    else:
        # Process specified modules and their submodules
        for module in args.modules:
            modules_to_process.append(module)
            # Also find submodules
            submodules = find_all_modules(module)
            modules_to_process.extend(submodules)

    # Remove duplicates
    modules_to_process = sorted(set(modules_to_process))

    # Generate documentation
    generated_modules = []
    failed_modules = []

    start_time = time.time()

    for i, module_name in enumerate(modules_to_process, 1):
        # Skip internal modules
        if not should_include_module(module_name):
            print(
                f"[{i}/{len(modules_to_process)}] Skipping {module_name} (internal module)"
            )
            continue

        source_file = get_module_source_file(module_name)
        if not source_file:
            print(
                f"[{i}/{len(modules_to_process)}] Skipping {module_name} (no source file)"
            )
            continue

        try:
            print(
                f"[{i}/{len(modules_to_process)}] Processing {module_name}...",
                end="",
                flush=True,
            )
            module_start = time.time()

            module_info = parse_module_fast(module_name, source_file)

            # Check if this module has submodules
            has_submodules = any(
                m.startswith(module_name + ".")
                and m.count(".") == module_name.count(".") + 1
                for m in modules_to_process
            )

            # If it has submodules, save it as __init__
            if has_submodules:
                output_file = (
                    args.output_dir / f"{module_name.replace('.', '-')}-__init__.mdx"
                )
            else:
                output_file = args.output_dir / f"{module_name.replace('.', '-')}.mdx"

            generate_mdx(module_info, output_file)

            module_time = time.time() - module_start
            print(f" done ({module_time:.2f}s)")

            generated_modules.append(module_name)
        except Exception as e:
            print(f" failed: {e}")
            failed_modules.append((module_name, str(e)))

    total_time = time.time() - start_time

    # Update navigation if requested
    if args.update_nav and generated_modules:
        docs_json_path = Path("docs/docs.json")
        if docs_json_path.exists():
            print("\nUpdating docs.json navigation...")
            # Only do complete regeneration when --all is used
            regenerate_all = args.all or (not args.modules)
            update_docs_json(
                docs_json_path, generated_modules, regenerate_all=regenerate_all
            )
            print("Navigation updated successfully")
        else:
            print(f"\nWarning: Could not find {docs_json_path}")

    # Summary
    print("\nGeneration complete!")
    print(f"  Total time: {total_time:.2f}s")
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