"""Base language server manager interface."""

import abc
import json
import logging
import os
import queue
import threading
from typing import Any, Callable, Dict, List, TypeAlias

# LSP message types
LspRequestCallback: TypeAlias = Callable[[Dict[str, Any]], None]


class BaseLanguageServerManager(abc.ABC):
    """Abstract base class for language server managers.

    This class defines the interface that all language server managers must implement.
    """

    def __init__(self, workspace_path: str):
        """Initialize the language server manager.

        Args:
            workspace_path: Path to the workspace directory.
        """
        self.workspace_path = os.path.abspath(workspace_path)
        self.logger = logging.getLogger(f"multilsp.servers.{self.language}")
        self.server_process = None

        # LSP communication
        self.request_callbacks: Dict[str, LspRequestCallback] = {}
        self.next_request_id = 1
        self.response_queue = queue.Queue()
        self.reader_thread = None
        self.writer_thread = None
        self.write_queue = queue.Queue()
        self.running = False
        self.initialization_options = {}

    @property
    @abc.abstractmethod
    def language(self) -> str:
        """Get the language managed by this server.

        Returns:
            The language name.
        """
        pass

    @abc.abstractmethod
    def start(self) -> None:
        """Start the language server process."""
        pass

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the language server process."""
        pass

    @abc.abstractmethod
    def is_running(self) -> bool:
        """Check if the language server is running.

        Returns:
            True if the server is running, False otherwise.
        """
        pass

    @abc.abstractmethod
    def run_linter(self, file_path: str) -> Dict[str, Any]:
        """Run linter on the specified file.

        Args:
            file_path: Path to the file to lint.

        Returns:
            Dictionary containing linting results.
        """
        pass

    @abc.abstractmethod
    def run_formatter(self, file_path: str) -> str:
        """Run formatter on the specified file.

        Args:
            file_path: Path to the file to format.

        Returns:
            Formatted content of the file.
        """
        pass

    def _start_lsp_communication(self) -> None:
        """Start LSP communication threads."""
        if not self.server_process:
            self.logger.error("Cannot start LSP communication: server process is not running")
            return

        self.running = True

        # Start reader thread
        self.reader_thread = threading.Thread(
            target=self._lsp_reader,
            daemon=True,
            name=f"{self.language}-lsp-reader"
        )
        self.reader_thread.start()

        # Start writer thread
        self.writer_thread = threading.Thread(
            target=self._lsp_writer,
            daemon=True,
            name=f"{self.language}-lsp-writer"
        )
        self.writer_thread.start()

        # Initialize the LSP server
        self._initialize_lsp_server()

    def _stop_lsp_communication(self) -> None:
        """Stop LSP communication threads."""
        self.running = False

        # Send shutdown request
        self._send_shutdown_request()

        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2)

        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=2)

    def _lsp_reader(self) -> None:
        """Read responses from the LSP server."""
        if not self.server_process or not self.server_process.stdout:
            self.logger.error("Cannot read from LSP server: server process or stdout is None")
            return

        while self.running and self.server_process.poll() is None:
            try:
                # Read the header
                line = self.server_process.stdout.readline().strip()
                if not line:
                    continue

                if line.startswith(b"Content-Length:"):
                    content_length = int(line.split(b":")[1])

                    # TODO: this is sketchy. For pylsp, we need to skip 2 empty lines after the header.
                    # Not sure what is required for other servers.
                    self.server_process.stdout.readline()
                    if self.language == "python":
                        self.server_process.stdout.readline()

                    # Read the content
                    content = self.server_process.stdout.read(content_length)
                    message = json.loads(content.decode("utf-8"))

                    self.logger.debug(f"Received LSP message: {message}")

                    # Process the message
                    self._process_lsp_message(message)

            except Exception as e:
                self.logger.error(f"Error reading from LSP server: {e}")
                break

    def _lsp_writer(self) -> None:
        """Write requests to the LSP server."""
        if not self.server_process or not self.server_process.stdin:
            self.logger.error("Cannot write to LSP server: server process or stdin is None")
            return

        while self.running and self.server_process.poll() is None:
            try:
                # Wait for a message to send
                message = self.write_queue.get(timeout=0.5)

                if message:
                    content = json.dumps(message).encode("utf-8")
                    header = f"Content-Length: {len(content)}\r\n\r\n".encode()

                    self.logger.debug(f"Sending LSP message: {message}")

                    self.server_process.stdin.write(header + content)
                    self.server_process.stdin.flush()

                self.write_queue.task_done()

            except queue.Empty:
                # No message to send, continue waiting
                continue
            except Exception as e:
                self.logger.error(f"Error writing to LSP server: {e}")
                break

    def _process_lsp_message(self, message: Dict[str, Any]) -> None:
        """Process a message from the LSP server.

        Args:
            message: The message from the LSP server.
        """
        # Check if it's a response to a request
        if "id" in message and "result" in message:
            request_id = str(message["id"])
            if request_id in self.request_callbacks:
                callback = self.request_callbacks.pop(request_id)
                callback(message)
            else:
                # Put the message in the response queue for synchronous requests
                self.response_queue.put(message)

        # Handle notifications (messages without an id)
        elif "method" in message and "id" not in message:
            self._handle_notification(message)

    def _handle_notification(self, notification: Dict[str, Any]) -> None:
        """Handle a notification from the LSP server.

        Args:
            notification: The notification from the LSP server.
        """
        method = notification.get("method", "")

        if method == "window/logMessage":
            params = notification.get("params", {})
            message_type = params.get("type", 4)  # Default to log
            message = params.get("message", "")

            log_levels = {
                1: logging.ERROR,
                2: logging.WARNING,
                3: logging.INFO,
                4: logging.DEBUG
            }

            level = log_levels.get(message_type, logging.INFO)
            self.logger.log(level, f"LSP server: {message}")

    def _initialize_lsp_server(self) -> None:
        """Initialize the LSP server."""
        # Create and send initialization request
        params = {
            "processId": os.getpid(),
            "rootPath": self.workspace_path,
            "rootUri": f"file://{self.workspace_path}",
            "capabilities": {
                "textDocument": {
                    "synchronization": {
                        "didSave": True,
                        "willSave": True
                    },
                    "completion": {
                        "completionItem": {
                            "snippetSupport": True
                        }
                    },
                    "signatureHelp": {},
                    "definition": {},
                    "references": {},
                    "documentHighlight": {},
                    "formatting": {},
                    "rangeFormatting": {},
                    "onTypeFormatting": {},
                    "rename": {},
                    "publishDiagnostics": {}
                },
                "workspace": {
                    "applyEdit": True,
                    "workspaceEdit": {
                        "documentChanges": True
                    },
                    "didChangeConfiguration": {},
                    "didChangeWatchedFiles": {}
                }
            },
            "initializationOptions": self.initialization_options,
            "trace": "verbose"
        }

        # Send the request and wait for the response
        response = self._send_request_sync("initialize", params)

        if response and "result" in response:
            # Send initialized notification
            self._send_notification("initialized", {})

            # Send workspace/didChangeConfiguration notification
            self._send_notification("workspace/didChangeConfiguration", {
                "settings": {}
            })

            self.logger.info(f"Successfully initialized {self.language} LSP server")
        else:
            self.logger.error(f"Failed to initialize {self.language} LSP server")

    def _send_shutdown_request(self) -> None:
        """Send shutdown request to the LSP server."""
        # Send shutdown request
        response = self._send_request_sync("shutdown", {})

        if response and "result" in response:
            # Send exit notification
            self._send_notification("exit", {})
            self.logger.info(f"Successfully shut down {self.language} LSP server")
        else:
            self.logger.error(f"Failed to shut down {self.language} LSP server")

    def _send_request_sync(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the LSP server and wait for the response.

        Args:
            method: The LSP method to call.
            params: Parameters for the method.

        Returns:
            Dictionary containing the response.
        """
        request_id = str(self.next_request_id)
        self.next_request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }

        # Put the request in the write queue
        self.write_queue.put(request)

        # Wait for the response
        try:
            response = self.response_queue.get(timeout=10)
            self.response_queue.task_done()
            return response
        except queue.Empty:
            self.logger.error(f"Timeout waiting for response to {method} request")
            return {}

    def _send_request_async(self, method: str, params: Dict[str, Any], callback: LspRequestCallback) -> None:
        """Send a request to the LSP server asynchronously.

        Args:
            method: The LSP method to call.
            params: Parameters for the method.
            callback: Function to call when the response is received.
        """
        request_id = str(self.next_request_id)
        self.next_request_id += 1

        # Store the callback
        self.request_callbacks[request_id] = callback

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }

        # Put the request in the write queue
        self.write_queue.put(request)

    def _send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send a notification to the LSP server.

        Args:
            method: The LSP method to call.
            params: Parameters for the method.
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }

        # Put the notification in the write queue
        self.write_queue.put(notification)

    def _uri_to_path(self, uri: str) -> str:
        """Convert a file URI to a file path.

        Args:
            uri: File URI to convert.

        Returns:
            File path.
        """
        if uri.startswith("file://"):
            return uri[7:]
        return uri

    def _path_to_uri(self, path: str) -> str:
        """Convert a file path to a file URI.

        Args:
            path: File path to convert.

        Returns:
            File URI.
        """
        return f"file://{os.path.abspath(path)}"

    def get_definition(self, file_path: str, line: int, character: int) -> Dict[str, Any]:
        """Get definition for the symbol at the specified position.

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
                "uri": self._path_to_uri(file_path)
            },
            "position": {
                "line": line,
                "character": character
            }
        }

        # Send request to language server
        response = self._send_request_sync("textDocument/definition", params)

        # Process the response
        result = response.get("result", None)

        # Handle different response formats (single location or array of locations)
        if isinstance(result, list):
            # Array of locations
            locations = []
            for location in result:
                uri = location.get("uri", "")
                range_data = location.get("range", {})
                locations.append({
                    "path": self._uri_to_path(uri),
                    "range": range_data
                })
            return {"locations": locations}

        if isinstance(result, dict):
            # Single location
            uri = result.get("uri", "")
            range_data = result.get("range", {})
            return {
                "locations": [{
                    "path": self._uri_to_path(uri),
                    "range": range_data
                }]
            }

        # No definition found
        return {"locations": []}

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
                "uri": self._path_to_uri(file_path)
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
        response = self._send_request_sync("textDocument/references", params)

        # Process the response
        result = response.get("result", [])

        # Convert to a more convenient format
        references = []
        for reference in result:
            uri = reference.get("uri", "")
            range_data = reference.get("range", {})
            references.append({
                "path": self._uri_to_path(uri),
                "range": range_data
            })

        return references
