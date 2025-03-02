#!/usr/bin/env python3
"""Main service module for the Multi-Language LSP Interface.

This module provides the primary service that manages multiple language servers
and routes client requests to the appropriate server based on file type.
"""

import logging
import os
from typing import Any, Dict, List, Optional, TypeAlias

import click

from multilsp.servers.javascript_server import JavaScriptLanguageServerManager
from multilsp.servers.python_server import PythonLanguageServerManager
from multilsp.utils.workspace import WorkspaceManager

# Type aliases
LanguageServerManagerType: TypeAlias = Any  # Simplified for now

class MultiLanguageServer:
    """Main service class that manages multiple language servers."""

    def __init__(self, workspace_path: str):
        """Initialize the multi-language server with a workspace path.

        Args:
            workspace_path: Path to the workspace directory to analyze.
        """
        self.workspace_path = os.path.abspath(workspace_path)
        self.workspace = WorkspaceManager(self.workspace_path)
        self.logger = logging.getLogger("multilsp")

        # Initialize language server managers
        self.server_managers: Dict[str, LanguageServerManagerType] = {
            "python": PythonLanguageServerManager(self.workspace_path),
            "javascript": JavaScriptLanguageServerManager(self.workspace_path),
            # TODO: java not supported yet, need to find a simpler way to install dependencies
            # "java": JavaLanguageServerManager(self.workspace_path),
        }

        self.logger.info(f"Initialized MultiLanguageServer for workspace: {self.workspace_path}")

    def start(self) -> None:
        """Start all language servers."""
        for lang, manager in self.server_managers.items():
            self.logger.info(f"Starting {lang} language server...")
            manager.start()

    def stop(self) -> None:
        """Stop all language servers."""
        for lang, manager in self.server_managers.items():
            self.logger.info(f"Stopping {lang} language server...")
            manager.stop()

    def get_server_for_file(self, file_path: str) -> Optional[LanguageServerManagerType]:
        """Get the appropriate language server for a given file.

        Args:
            file_path: Path to the file to analyze.

        Returns:
            The appropriate language server manager or None if no server supports this file.
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        # Map file extensions to language servers
        ext_to_server = {
            ".py": self.server_managers["python"],
            ".js": self.server_managers["javascript"],
            ".ts": self.server_managers["javascript"],
            ".jsx": self.server_managers["javascript"],
            ".tsx": self.server_managers["javascript"],
            ".java": self.server_managers["java"],
        }

        return ext_to_server.get(file_ext)

    def run_linter(self, file_path: str) -> Dict[str, Any]:
        """Run linter on the specified file.

        Args:
            file_path: Path to the file to lint.

        Returns:
            Dictionary containing linting results.

        Raises:
            ValueError: If no appropriate language server is found for the file.
        """
        server = self.get_server_for_file(file_path)
        if not server:
            raise ValueError(f"No language server found for file: {file_path}")

        return server.run_linter(file_path)

    def run_formatter(self, file_path: str) -> str:
        """Run formatter on the specified file.

        Args:
            file_path: Path to the file to format.

        Returns:
            Formatted content of the file.

        Raises:
            ValueError: If no appropriate language server is found for the file.
        """
        server = self.get_server_for_file(file_path)
        if not server:
            raise ValueError(f"No language server found for file: {file_path}")

        return server.run_formatter(file_path)

    def get_definition(self, file_path: str, line: int, character: int) -> Dict[str, Any]:
        """Get definition for the symbol at the specified position.

        Args:
            file_path: Path to the file.
            line: Line number (0-indexed).
            character: Character position (0-indexed).

        Returns:
            Dictionary containing definition information.

        Raises:
            ValueError: If no appropriate language server is found for the file.
        """
        server = self.get_server_for_file(file_path)
        if not server:
            raise ValueError(f"No language server found for file: {file_path}")

        return server.get_definition(file_path, line, character)

    def get_references(self, file_path: str, line: int, character: int) -> List[Dict[str, Any]]:
        """Get references for the symbol at the specified position.

        Args:
            file_path: Path to the file.
            line: Line number (0-indexed).
            character: Character position (0-indexed).

        Returns:
            List of dictionaries containing reference information.

        Raises:
            ValueError: If no appropriate language server is found for the file.
        """
        server = self.get_server_for_file(file_path)
        if not server:
            raise ValueError(f"No language server found for file: {file_path}")

        return server.get_references(file_path, line, character)


@click.command()
@click.option("--workspace", required=True, help="Path to the workspace directory")
@click.option("--debug/--no-debug", default=False, help="Enable debug logging")
def main(workspace: str, debug: bool) -> None:
    """Run the Multi-Language LSP service.

    Args:
        workspace: Path to the workspace directory.
        debug: Whether to enable debug logging.
    """
    # Configure logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Initialize and start the service
    service = MultiLanguageServer(workspace)
    try:
        service.start()
        click.echo(f"MultiLanguageServer started for workspace: {workspace}")
        # Keep the service running until Ctrl+C
        click.echo("Press Ctrl+C to stop the service")
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("Stopping service...")
    finally:
        service.stop()
        click.echo("Service stopped")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
