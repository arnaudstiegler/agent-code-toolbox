"""Workspace management utilities for the Multi-Language LSP Interface."""

import logging
import os
from typing import Dict, List, Optional, Set


class WorkspaceManager:
    """Manages workspace information and file tracking."""

    def __init__(self, workspace_path: str):
        """Initialize the workspace manager.

        Args:
            workspace_path: Path to the workspace directory.
        """
        self.workspace_path = os.path.abspath(workspace_path)
        self.logger = logging.getLogger("multilsp.workspace")

        if not os.path.isdir(self.workspace_path):
            raise ValueError(f"Workspace path is not a directory: {self.workspace_path}")

        self.logger.info(f"Initialized workspace manager for: {self.workspace_path}")

        # Track files by language
        self.files_by_language: Dict[str, Set[str]] = {
            "python": set(),
            "javascript": set(),
            "java": set(),
        }

        # Map file extensions to languages
        self.extension_to_language = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "javascript",
            ".jsx": "javascript",
            ".tsx": "javascript",
            ".java": "java",
        }

        # Scan workspace to discover files
        self._scan_workspace()

    def _scan_workspace(self) -> None:
        """Scan the workspace directory to discover files by language."""
        self.logger.info(f"Scanning workspace: {self.workspace_path}")

        for root, _, files in os.walk(self.workspace_path):
            for file in files:
                file_path = os.path.join(root, file)
                self._categorize_file(file_path)

    def _categorize_file(self, file_path: str) -> None:
        """Categorize a file by its language based on extension.

        Args:
            file_path: Path to the file to categorize.
        """
        _, ext = os.path.splitext(file_path)
        language = self.extension_to_language.get(ext.lower())

        if language and language in self.files_by_language:
            self.files_by_language[language].add(file_path)

    def get_files_by_language(self, language: str) -> List[str]:
        """Get all files for a specific language.

        Args:
            language: The language to get files for.

        Returns:
            List of file paths for the specified language.
        """
        if language not in self.files_by_language:
            return []

        return list(self.files_by_language[language])

    def get_language_for_file(self, file_path: str) -> Optional[str]:
        """Get the language for a specific file.

        Args:
            file_path: Path to the file.

        Returns:
            The language for the file or None if not supported.
        """
        _, ext = os.path.splitext(file_path)
        return self.extension_to_language.get(ext.lower())

    def add_file(self, file_path: str) -> None:
        """Add a file to the workspace tracking.

        Args:
            file_path: Path to the file to add.
        """
        self._categorize_file(file_path)

    def remove_file(self, file_path: str) -> None:
        """Remove a file from the workspace tracking.

        Args:
            file_path: Path to the file to remove.
        """
        for language in self.files_by_language:
            self.files_by_language[language].discard(file_path)

    def is_file_in_workspace(self, file_path: str) -> bool:
        """Check if a file is in the workspace.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file is in the workspace, False otherwise.
        """
        abs_path = os.path.abspath(file_path)
        return abs_path.startswith(self.workspace_path)
