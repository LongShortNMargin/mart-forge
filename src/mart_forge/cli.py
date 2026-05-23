"""mart-forge CLI entry point."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="mart-forge",
        description="Methodology-first Kimball DWH scaffolding framework",
    )
    parser.add_argument("--version", action="version", version="mart-forge 3.0.0")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("validate", help="Validate framework templates and structure")
    subparsers.add_parser("scan", help="Run confidentiality scan")

    args = parser.parse_args()

    if args.command == "validate":
        from scripts.validate_templates import main as validate_main
        validate_main()
    elif args.command == "scan":
        from scripts.confidentiality_scan import main as scan_main
        scan_main()
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
