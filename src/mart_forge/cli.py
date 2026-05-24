"""mart-forge CLI entry point."""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="mart-forge",
        description="Methodology-first Kimball DWH scaffolding framework",
    )
    parser.add_argument("--version", action="version", version="mart-forge 3.0.0")

    subparsers = parser.add_subparsers(dest="command")

    scaffold_parser = subparsers.add_parser(
        "scaffold", help="Generate dbt project from signed BRD/TDD"
    )
    scaffold_parser.add_argument(
        "mart_dir", type=str, help="Path to mart directory containing brd.md and tdd.md"
    )
    scaffold_parser.add_argument(
        "--name", type=str, required=True, help="Mart name (kebab-case)"
    )
    scaffold_parser.add_argument(
        "--prefix", type=str, required=True, help="Model naming prefix (2-4 chars)"
    )
    scaffold_parser.add_argument(
        "--fixture", action="store_true", default=False,
        help="Generate CI smoke-fixture (built-in order/revenue templates) instead of general contract-driven scaffold",
    )

    validate_parser = subparsers.add_parser(
        "validate", help="Validate framework templates and structure"
    )

    scan_parser = subparsers.add_parser(
        "scan", help="Run generic confidentiality scan"
    )

    args = parser.parse_args()

    if args.command == "scaffold":
        from mart_forge.scaffold import scaffold

        mart_path = Path(args.mart_dir)
        if not mart_path.exists():
            print(f"Error: directory {mart_path} does not exist.")
            sys.exit(1)

        result = scaffold(mart_path, args.name, args.prefix, fixture=args.fixture)
        if not result["success"]:
            print("Scaffold REFUSED — hard gate violations:")
            for err in result["errors"]:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print(f"Scaffold complete: {len(result['files_created'])} files created.")
            for f in result["files_created"]:
                print(f"  {f}")

    elif args.command == "validate":
        from mart_forge.validate import validate_framework
        sys.exit(0 if validate_framework() else 1)

    elif args.command == "scan":
        from mart_forge.scan import run_scan
        sys.exit(0 if run_scan() else 1)

    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
