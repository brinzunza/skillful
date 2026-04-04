"""
Persistent memory management for agent conversations and state.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


MEMORY_DIR = ".skillful"
HISTORY_FILE = os.path.join(MEMORY_DIR, "history.json")
SESSIONS_FILE = os.path.join(MEMORY_DIR, "sessions.json")


class Memory:
    """Manages persistent storage of agent conversations and state."""

    def __init__(self):
        """Initialize memory system."""
        self._ensure_memory_dir()

    def _ensure_memory_dir(self):
        """Create memory directory if it doesn't exist."""
        os.makedirs(MEMORY_DIR, exist_ok=True)

    def save_conversation(self, conversation: List[Dict], session_name: Optional[str] = None) -> str:
        """
        Save conversation history to disk.

        Args:
            conversation: List of conversation messages
            session_name: Optional name for the session

        Returns:
            Session ID
        """
        if not conversation:
            return None

        # Generate session ID
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if session_name:
            session_id = f"{session_id}_{session_name}"

        # Load existing sessions
        sessions = self._load_sessions()

        # Add new session
        sessions.append({
            "id": session_id,
            "timestamp": datetime.now().isoformat(),
            "name": session_name or "Unnamed Session",
            "message_count": len(conversation),
            "conversation": conversation
        })

        # Save sessions
        self._save_sessions(sessions)

        return session_id

    def load_conversation(self, session_id: Optional[str] = None) -> List[Dict]:
        """
        Load conversation history from disk.

        Args:
            session_id: Session ID to load (None = most recent)

        Returns:
            List of conversation messages
        """
        sessions = self._load_sessions()

        if not sessions:
            return []

        if session_id is None:
            # Return most recent session
            return sessions[-1]["conversation"]

        # Find specific session
        for session in sessions:
            if session["id"] == session_id:
                return session["conversation"]

        return []

    def list_sessions(self) -> List[Dict]:
        """
        List all saved sessions.

        Returns:
            List of session metadata (without full conversation)
        """
        sessions = self._load_sessions()

        # Return metadata only
        return [{
            "id": s["id"],
            "timestamp": s["timestamp"],
            "name": s["name"],
            "message_count": s["message_count"]
        } for s in sessions]

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        sessions = self._load_sessions()

        # Find and remove session
        for i, session in enumerate(sessions):
            if session["id"] == session_id:
                sessions.pop(i)
                self._save_sessions(sessions)
                return True

        return False

    def clear_all(self):
        """Clear all saved sessions."""
        self._save_sessions([])

    def _load_sessions(self) -> List[Dict]:
        """Load all sessions from disk."""
        if not os.path.exists(SESSIONS_FILE):
            return []

        try:
            with open(SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_sessions(self, sessions: List[Dict]):
        """Save all sessions to disk."""
        try:
            with open(SESSIONS_FILE, 'w') as f:
                json.dump(sessions, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save sessions: {e}")

    def get_memory_stats(self) -> Dict:
        """
        Get statistics about stored memory.

        Returns:
            Dictionary with memory stats
        """
        sessions = self._load_sessions()

        if not sessions:
            return {
                "total_sessions": 0,
                "total_messages": 0,
                "oldest_session": None,
                "newest_session": None,
                "disk_usage_bytes": 0
            }

        total_messages = sum(s["message_count"] for s in sessions)

        # Calculate disk usage
        disk_usage = 0
        if os.path.exists(SESSIONS_FILE):
            disk_usage = os.path.getsize(SESSIONS_FILE)

        return {
            "total_sessions": len(sessions),
            "total_messages": total_messages,
            "oldest_session": sessions[0]["timestamp"],
            "newest_session": sessions[-1]["timestamp"],
            "disk_usage_bytes": disk_usage
        }
