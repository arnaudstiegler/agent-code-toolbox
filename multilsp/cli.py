#!/usr/bin/env python3
"""Command-line interface for the Multi-Language LSP Interface."""

import argparse
import logging
import sys
from typing import List, Optional

from multilsp.service import MultiLanguageServer


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command-line arguments. If None, sys.argv is used.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Multi-Language LSP Interface CLI"
    )

    # Add workspace argument
    parser.add_argument(
        "--workspace",
        "-w",
        required=True,
        help="Path to the workspace directory to analyze"
    )

    # Add action subparsers
    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # Linter subcommand
    lint_parser = subparsers.add_parser("lint", help="Run linter on a file")
    lint_parser.add_argument("file", help="Path to the file to lint")

    # Formatter subcommand
    format_parser = subparsers.add_parser("format", help="Run formatter on a file")
    format_parser.add_argument("file", help="Path to the file to format")

    # Definition subcommand
    def_parser = subparsers.add_parser("definition", help="Get definition for a symbol")
    def_parser.add_argument("file", help="Path to the file")
    def_parser.add_argument("line", type=int, help="Line number (0-indexed)")
    def_parser.add_argument("character", type=int, help="Character position (0-indexed)")

    # References subcommand
    ref_parser = subparsers.add_parser("references", help="Get references for a symbol")
    ref_parser.add_argument("file", help="Path to the file")
    ref_parser.add_argument("line", type=int, help="Line number (0-indexed)")
    ref_parser.add_argument("character", type=int, help="Character position (0-indexed)")

    # Server subcommand
    _server_parser = subparsers.add_parser("server", help="Run as a server")  # type: ignore

    # Add debug flag
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    """Run the CLI application.

    Args:
        args: Command-line arguments. If None, sys.argv is used.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parsed_args = parse_args(args)

    # Configure logging
    log_level = logging.DEBUG if parsed_args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create the service
    service = MultiLanguageServer(parsed_args.workspace)

    try:
        if parsed_args.action == "lint":
            result = service.run_linter(parsed_args.file)
            print(result)
            return 0

        if parsed_args.action == "format":
            formatted = service.run_formatter(parsed_args.file)
            print(formatted)
            return 0

        if parsed_args.action == "definition":
            result = service.get_definition(
                parsed_args.file,
                parsed_args.line,
                parsed_args.character
            )
            print(result)
            return 0

        if parsed_args.action == "references":
            result = service.get_references(
                parsed_args.file,
                parsed_args.line,
                parsed_args.character
            )
            print(result)
            return 0

        if parsed_args.action == "server":
            # Start as a server
            service.start()

            try:
                print(f"Multi-Language LSP Interface server started for workspace: {parsed_args.workspace}")
                print("Press Ctrl+C to stop the server")

                # Keep the server running until Ctrl+C
                import time
                while True:
                    time.sleep(1)

            except KeyboardInterrupt:
                print("Stopping server...")
            finally:
                service.stop()
                print("Server stopped")

            return 0

        print("Please specify an action. Use --help for available commands.")
        return 1

    except Exception as e:
        logging.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
