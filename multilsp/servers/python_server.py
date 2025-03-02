"""Python language server manager implementation."""

import json
import os
import subprocess
from typing import Any, Dict, List

from multilsp.servers.base import BaseLanguageServerManager


class PythonLanguageServerManager(BaseLanguageServerManager):
    """Manages the Python language server."""

    @property
    def language(self) -> str:
        """Get the language managed by this server.

        Returns:
            The language name.
        """
        return "python"

    def __init__(self, workspace_path: str):
        """Initialize the Python language server manager.

        Args:
            workspace_path: Path to the workspace directory.
        """
        # Initialize language-specific settings before calling parent constructor
        self.initialization_options = {
            "plugins": {
                "jedi": {
                    "enabled": True
                },
                "pylint": {
                    "enabled": True,
                    "executable": "pylint"
                },
                "pycodestyle": {
                    "enabled": True
                },
                "black": {
                    "enabled": True
                }
            }
        }

        # Call parent constructor
        super().__init__(workspace_path)
        self.server_process = None
        self.server_command = ["pylsp"]
        self.pylint_cmd = ["pylint", "--output-format=json"]
        self.black_cmd = ["black", "-"]

        # Set server-specific configuration
        self._server_settings = {
            "pylsp": {
                "plugins": {
                    "jedi": {
                        "enabled": True
                    },
                    "pylint": {
                        "enabled": True,
                        "executable": "pylint"
                    },
                    "pycodestyle": {
                        "enabled": True
                    },
                    "black": {
                        "enabled": True
                    }
                }
            }
        }

    def start(self) -> None:
        """Start the Python language server process."""
        if self.is_running():
            self.logger.info("Python language server is already running")
            return

        try:
            # Start the language server in a subprocess
            self.logger.info(f"Starting Python language server with command: {' '.join(self.server_command)}")
            self.server_process = subprocess.Popen(
                self.server_command,
                cwd=self.workspace_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            self.logger.info("Python language server started successfully")

            # Start LSP communication
            self._start_lsp_communication()

            # Configure the server
            self._configure_server()
        except Exception as e:
            self.logger.error(f"Failed to start Python language server: {e}")
            raise

    def stop(self) -> None:
        """Stop the Python language server process."""
        # Stop LSP communication first
        self._stop_lsp_communication()

        if self.server_process and self.server_process.poll() is None:
            self.logger.info("Stopping Python language server")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.logger.warning("Python language server did not terminate, forcing kill")
                self.server_process.kill()

            self.server_process = None
            self.logger.info("Python language server stopped")

    def is_running(self) -> bool:
        """Check if the Python language server is running.

        Returns:
            True if the server is running, False otherwise.
        """
        return self.server_process is not None and self.server_process.poll() is None

    def _configure_server(self) -> None:
        """Configure the Python language server."""
        # Send didChangeConfiguration notification with our settings
        self._send_notification("workspace/didChangeConfiguration", {
            "settings": self._server_settings
        })

    def run_linter(self, file_path: str) -> Dict[str, Any]:
        """Run Pylint on the specified file using LSP.

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
        # 2. Run pylint directly as before

        # Approach 1: Use LSP diagnostics
        # We need to open the document in the LSP server to trigger diagnostics
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Send didOpen notification
        document_uri = self._path_to_uri(file_path)
        self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": document_uri,
                "languageId": "python",
                "version": 1,
                "text": content
            }
        })

        # We could wait for diagnostics here, but the server doesn't have a standard way to request them
        # For now, we'll fall back to the direct pylint approach

        # Approach 2: Run pylint directly
        cmd = self.pylint_cmd + [file_path]

        try:
            process = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit code
            )

            if process.returncode != 0 and process.returncode != 1:
                # pylint returns 1 when it finds linting issues, which is expected
                # Any other non-zero return code is an error
                self.logger.error(f"Pylint error (code {process.returncode}): {process.stderr}")

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
                self.logger.error(f"Error parsing pylint output: {e}")
                return {
                    "issues": [],
                    "success": False,
                    "error": f"Error parsing linter output: {str(e)}",
                    "raw_output": process.stdout
                }

        except Exception as e:
            self.logger.error(f"Error running pylint: {e}")
            return {
                "issues": [],
                "success": False,
                "error": str(e)
            }

    def run_formatter(self, file_path: str) -> str:
        """Run Black formatter on the specified file using LSP.

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
        # 2. Run black directly as before

        # Approach 1: Use LSP formatting
        # First, open the document in the LSP server
        document_uri = self._path_to_uri(file_path)
        self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": document_uri,
                "languageId": "python",
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
                    "tabSize": 4,
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
            self.logger.info("No formatting changes from LSP server, falling back to direct black formatter")

        except Exception as e:
            self.logger.error(f"Error during LSP formatting: {e}, falling back to direct black formatter")

        # Approach 2: Run black directly
        try:
            process = subprocess.run(
                self.black_cmd,
                input=content,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit code
            )

            if process.returncode == 0:
                return process.stdout

            self.logger.error(f"Black formatter error: {process.stderr}")
            # Return original content if formatting fails
            return content

        except Exception as e:
            self.logger.error(f"Error running black formatter: {e}")
            # Return original content if formatting fails
            return content

    def get_definition(self, file_path: str, line: int, character: int) -> Dict[str, Any]:
        """Get definition for the symbol at the specified position using Jedi.

        Args:
            file_path: Path to the file.
            line: Line number (0-indexed).
            character: Character position (0-indexed).

        Returns:
            Dictionary containing definition information.
        """
        self.logger.info(f"Getting definition in file: {file_path} at position {line}:{character}")

        # Ensure the language server is running
        if not self.is_running():
            self.start()

        # Prepare LSP request parameters
        params = {
            "textDocument": {
                "uri": f"file://{os.path.abspath(file_path)}"
            },
            "position": {
                "line": line,
                "character": character
            }
        }

        # Send request to language server
        response = self._send_lsp_request("textDocument/definition", params)

        return response.get("result", {})

    def get_references(self, file_path: str, line: int, character: int) -> List[Dict[str, Any]]:
        """Get references for the symbol at the specified position.

        Args:
            file_path: Path to the file.
            line: Line number (0-indexed).
            character: Character position (0-indexed).

        Returns:
            List of dictionaries containing reference information.
        """
        self.logger.info(f"Getting references in file: {file_path} at position {line}:{character}")

        # Ensure the language server is running
        if not self.is_running():
            self.start()

        # Prepare LSP request parameters
        params = {
            "textDocument": {
                "uri": f"file://{os.path.abspath(file_path)}"
            },
            "position": {
                "line": line,
                "character": character
            },
            "context": {
                "includeDeclaration": True
            }
        }

        # Send request to language server
        response = self._send_lsp_request("textDocument/references", params)

        return response.get("result", [])
