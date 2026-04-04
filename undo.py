"""
Undo/rollback functionality with git integration.
"""

import os
import subprocess
from typing import Optional, List, Tuple
from datetime import datetime


class UndoManager:
    """Manages undo/rollback operations using git."""

    def __init__(self, use_git: bool = True, auto_commit: bool = True):
        """
        Initialize undo manager.

        Args:
            use_git: Whether to use git for undo
            auto_commit: Whether to auto-commit before operations
        """
        self.use_git = use_git
        self.auto_commit = auto_commit
        self.operation_stack = []

        if use_git:
            self._ensure_git_repo()

    def _ensure_git_repo(self):
        """Ensure we're in a git repository."""
        if not os.path.exists('.git'):
            try:
                subprocess.run(['git', 'init'], check=True, capture_output=True)
                # Create .gitignore if doesn't exist
                if not os.path.exists('.gitignore'):
                    with open('.gitignore', 'w') as f:
                        f.write(".skillful/\n")
                subprocess.run(['git', 'add', '.gitignore'], check=True, capture_output=True)
                subprocess.run(
                    ['git', 'commit', '-m', 'Initial commit by Skillful'],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError:
                self.use_git = False

    def checkpoint(self, description: str) -> Optional[str]:
        """
        Create a checkpoint before an operation.

        Args:
            description: Description of the operation

        Returns:
            Checkpoint ID (git commit hash) or None if failed
        """
        if not self.use_git or not self.auto_commit:
            return None

        try:
            # Stage all changes
            subprocess.run(['git', 'add', '-A'], check=True, capture_output=True)

            # Check if there are changes to commit
            result = subprocess.run(
                ['git', 'diff', '--staged', '--quiet'],
                capture_output=True
            )

            if result.returncode == 0:
                # No changes to commit
                return self._get_current_commit()

            # Create commit
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"[Skillful Checkpoint] {description}\n\nTimestamp: {timestamp}"

            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                check=True,
                capture_output=True
            )

            # Get commit hash
            commit_hash = self._get_current_commit()

            # Add to operation stack
            self.operation_stack.append({
                "commit": commit_hash,
                "description": description,
                "timestamp": timestamp
            })

            return commit_hash

        except subprocess.CalledProcessError:
            return None

    def undo_last(self) -> Tuple[bool, str]:
        """
        Undo the last operation.

        Returns:
            Tuple of (success, message)
        """
        if not self.use_git:
            return False, "Git undo is not enabled"

        if not self.operation_stack:
            return False, "No operations to undo"

        try:
            # Get last operation
            last_op = self.operation_stack[-1]

            # Reset to that commit
            subprocess.run(
                ['git', 'reset', '--hard', last_op['commit']],
                check=True,
                capture_output=True
            )

            # Remove from stack
            self.operation_stack.pop()

            return True, f"Undone: {last_op['description']}"

        except subprocess.CalledProcessError as e:
            return False, f"Failed to undo: {str(e)}"

    def get_history(self) -> List[dict]:
        """
        Get undo history.

        Returns:
            List of operations
        """
        return self.operation_stack.copy()

    def _get_current_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def get_git_status(self) -> str:
        """
        Get git status.

        Returns:
            Git status output
        """
        if not self.use_git:
            return "Git is not enabled"

        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout or "Working tree clean"
        except subprocess.CalledProcessError:
            return "Error getting git status"

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self.use_git and len(self.operation_stack) > 0
