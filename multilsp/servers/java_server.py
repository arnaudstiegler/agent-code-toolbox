"""Java language server manager implementation."""

import json
import os
import subprocess
from typing import Any, Dict

from multilsp.servers.base import BaseLanguageServerManager


class JavaLanguageServerManager(BaseLanguageServerManager):
    """Manages the Java language server."""

    @property
    def language(self) -> str:
        """Get the language managed by this server.

        Returns:
            The language name.
        """
        return "java"

    def __init__(self, workspace_path: str):
        """Initialize the Java language server manager.

        Args:
            workspace_path: Path to the workspace directory.
        """
        # Initialize language-specific settings before calling parent constructor
        self.initialization_options = {
            "settings": {
                "java": {
                    "format": {
                        "enabled": True,
                        "settings": {
                            "profile": "GoogleStyle"
                        }
                    }
                }
            }
        }

        # Call parent constructor
        super().__init__(workspace_path)
        self.server_process = None
        # Eclipse JDT Language Server
        self.server_command = ["java", "-jar", "/path/to/eclipse.jdt.ls.jar", "--stdio"]
        # Use Google Java Format for formatting
        self.formatter_cmd = ["java", "-jar", "/path/to/google-java-format.jar"]
        # CheckStyle for linting
        self.linter_cmd = ["java", "-jar", "/path/to/checkstyle.jar", "-f", "json"]

        # Set server-specific configuration
        self._server_settings = {
            "java": {
                "configuration": {
                    "updateBuildConfiguration": "automatic"
                },
                "format": {
                    "enabled": True,
                    "settings": {
                        "profile": "GoogleStyle"
                    }
                },
                "completion": {
                    "enabled": True,
                    "guessMethodArguments": True
                },
                "codeGeneration": {
                    "useBlocks": True,
                    "generateComments": True
                }
            }
        }

    def start(self) -> None:
        """Start the Java language server process."""
        if self.is_running():
            self.logger.info("Java language server is already running")
            return

        try:
            # Start the language server in a subprocess
            self.logger.info(f"Starting Java language server with command: {' '.join(self.server_command)}")
            self.server_process = subprocess.Popen(
                self.server_command,
                cwd=self.workspace_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            self.logger.info("Java language server started successfully")

            # Start LSP communication
            self._start_lsp_communication()

            # Configure the server
            self._configure_server()
        except Exception as e:
            self.logger.error(f"Failed to start Java language server: {e}")
            raise

    def stop(self) -> None:
        """Stop the Java language server process."""
        # Stop LSP communication first
        self._stop_lsp_communication()

        if self.server_process and self.server_process.poll() is None:
            self.logger.info("Stopping Java language server")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning("Java language server did not terminate, forcing kill")
                self.server_process.kill()

            self.server_process = None
            self.logger.info("Java language server stopped")

    def is_running(self) -> bool:
        """Check if the Java language server is running.

        Returns:
            True if the server is running, False otherwise.
        """
        return self.server_process is not None and self.server_process.poll() is None

    def _configure_server(self) -> None:
        """Configure the Java language server."""
        # Send didChangeConfiguration notification with our settings
        self._send_notification("workspace/didChangeConfiguration", {
            "settings": self._server_settings
        })

    def run_linter(self, file_path: str) -> Dict[str, Any]:
        """Run Checkstyle on the specified file using LSP.

        Args:
            file_path: Path to the file to lint.

        Returns:
            Dictionary containing linting results.
        """
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found: {file_path}")

        self.logger.info(f"Running linter on file: {file_path}")

        # Ensure the server is running
        if not self.is_running():
            self.start()

        # Two approaches are possible:
        # 1. Use the LSP server's built-in linting capabilities
        # 2. Run checkstyle directly as before

        # Approach 1: Use LSP diagnostics
        # We need to open the document in the LSP server to trigger diagnostics
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Send didOpen notification
        document_uri = self._path_to_uri(file_path)
        self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": document_uri,
                "languageId": "java",
                "version": 1,
                "text": content
            }
        })

        # Eclipse JDT LS doesn't have a standard way to request diagnostics directly
        # For now, we'll fall back to the direct checkstyle approach

        # Approach 2: Run checkstyle directly
        cmd = self.linter_cmd + [file_path]

        try:
            process = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit code
            )

            # Parse JSON output
            try:
                if process.stdout.strip():
                    results = json.loads(process.stdout)
                else:
                    results = []

                return {
                    "issues": results,
                    "success": True
                }
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing checkstyle output: {e}")
                return {
                    "issues": [],
                    "success": False,
                    "error": f"Error parsing linter output: {str(e)}",
                    "raw_output": process.stdout
                }

        except Exception as e:
            self.logger.error(f"Error running checkstyle: {e}")
            return {
                "issues": [],
                "success": False,
                "error": str(e)
            }

    def run_formatter(self, file_path: str) -> str:
        """Run Google Java Format on the specified file using LSP.

        Args:
            file_path: Path to the file to format.

        Returns:
            Formatted content of the file.
        """
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found: {file_path}")

        self.logger.info(f"Formatting file: {file_path}")

        # Ensure the server is running
        if not self.is_running():
            self.start()

        # Read the file content
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Two approaches are possible:
        # 1. Use the LSP server's formatting capabilities
        # 2. Run google-java-format directly as before

        # Approach 1: Use LSP formatting
        # First, open the document in the LSP server
        document_uri = self._path_to_uri(file_path)
        self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": document_uri,
                "languageId": "java",
                "version": 1,
                "text": content
            }
        })

        # Request formatting
        try:
            response = self._send_request_sync("textDocument/formatting", {
                "textDocument": {
                    "uri": document_uri
                },
                "options": {
                    "tabSize": 2,
                    "insertSpaces": True
                }
            })

            if response and "result" in response:
                result = response["result"]
                if result:
                    # Apply text edits
                    new_content = content
                    # Sort edits in reverse order to avoid invalidating offsets
                    for edit in sorted(result, key=lambda e: -1 * e["range"]["start"]["line"]):
                        range_start = edit["range"]["start"]
                        range_end = edit["range"]["end"]
                        new_text = edit["newText"]

                        # Convert to line and character offsets
                        lines = new_content.splitlines(True)  # Keep line endings

                        # Calculate character offsets
                        start_offset = sum(len(lines[i]) for i in range(range_start["line"])) + range_start["character"]
                        end_offset = sum(len(lines[i]) for i in range(range_end["line"])) + range_end["character"]

                        # Apply the edit
                        new_content = new_content[:start_offset] + new_text + new_content[end_offset:]

                    # Close the document
                    self._send_notification("textDocument/didClose", {
                        "textDocument": {
                            "uri": document_uri
                        }
                    })

                    return new_content

            # If we get here, either there were no edits or something went wrong
            self.logger.info("No formatting changes from LSP server, falling back to direct Java formatter")

        except Exception as e:
            self.logger.error(f"Error during LSP formatting: {e}, falling back to direct Java formatter")

        # Approach 2: Run google-java-format directly
        try:
            process = subprocess.run(
                self.formatter_cmd + [file_path],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit code
            )

            if process.returncode == 0:
                return process.stdout

            self.logger.error(f"Java formatter error: {process.stderr}")
            # If formatting fails, read and return original content
            return content

        except Exception as e:
            self.logger.error(f"Error running Java formatter: {e}")
            # If formatting fails, read and return original content
            return content
