"""Session manager for persistent conversation history.

Stores session metadata in a JSON Lines file and full conversation
data in SQLite databases per project.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver


@dataclass
class SessionInfo:
    """Metadata for a saved session."""

    session_id: str
    """Unique session identifier (UUID)."""

    agent_name: str
    """Agent identifier used for this session."""

    summary: str
    """Brief summary or first user message."""

    project_path: str
    """Absolute path to the project directory."""

    working_dir: str
    """Working directory when session was created."""

    created_at: str
    """ISO timestamp when session was created."""

    updated_at: str
    """ISO timestamp when session was last updated."""

    message_count: int
    """Number of messages in the session."""

    git_branch: str | None = None
    """Git branch name if in a git repository."""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "summary": self.summary,
            "project_path": self.project_path,
            "working_dir": self.working_dir,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count,
            "git_branch": self.git_branch,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionInfo":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            agent_name=data["agent_name"],
            summary=data["summary"],
            project_path=data["project_path"],
            working_dir=data["working_dir"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            message_count=data["message_count"],
            git_branch=data.get("git_branch"),
        )


@dataclass
class SessionManager:
    """Manages session persistence and retrieval.

    Sessions are stored in two locations:
    - ~/.deepagents/history.jsonl: Index of all sessions with metadata
    - ~/.deepagents/sessions/{project_hash}/{session_id}.db: SQLite checkpoints
    """

    deepagents_dir: Path
    """Base directory for DeepAgents data (~/.deepagents)."""

    history_file: Path = field(init=False)
    """Path to history.jsonl file."""

    sessions_dir: Path = field(init=False)
    """Directory for session SQLite files."""

    def __post_init__(self):
        """Initialize paths after dataclass creation."""
        self.history_file = self.deepagents_dir / "history.jsonl"
        self.sessions_dir = self.deepagents_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_git_branch(self) -> str | None:
        """Get current git branch name if in a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def _get_project_hash(self, project_path: str) -> str:
        """Generate a hash for the project path to organize sessions."""
        import hashlib

        return hashlib.sha256(project_path.encode()).hexdigest()[:12]

    def get_session_db_path(self, session_id: str, project_path: str) -> Path:
        """Get the SQLite database path for a session.

        Args:
            session_id: Session ID.
            project_path: Project path for hashing.

        Returns:
            Path to the SQLite database file.
        """
        project_hash = self._get_project_hash(project_path)
        project_dir = self.sessions_dir / project_hash
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir / f"{session_id}.db"

    def create_session(
        self,
        agent_name: str,
        project_path: str | None = None,
        summary: str = "",
    ) -> tuple[str, Path]:
        """Create a new session with persistent storage.

        Args:
            agent_name: Agent identifier.
            project_path: Project root path (defaults to cwd).
            summary: Optional summary for the session.

        Returns:
            Tuple of (session_id, db_path) for creating async checkpointer.
        """
        session_id = str(uuid.uuid4())
        project_path = project_path or str(Path.cwd())
        working_dir = str(Path.cwd())
        now = datetime.now().isoformat()

        # Create session info
        info = SessionInfo(
            session_id=session_id,
            agent_name=agent_name,
            summary=summary or "(new session)",
            project_path=project_path,
            working_dir=working_dir,
            created_at=now,
            updated_at=now,
            message_count=0,
            git_branch=self._get_git_branch(),
        )

        # Save to history index
        self._append_to_history(info)

        # Return session ID and db path for async checkpointer creation
        db_path = self.get_session_db_path(session_id, project_path)
        return session_id, db_path

    def get_session_db_path_by_id(self, session_id: str) -> Path | None:
        """Get database path for an existing session.

        Args:
            session_id: Session ID to load.

        Returns:
            Path to SQLite database if session exists, None otherwise.
        """
        info = self.get_session_info(session_id)
        if not info:
            return None

        return self.get_session_db_path(session_id, info.project_path)

    def get_session_info(self, session_id: str) -> SessionInfo | None:
        """Get session info by ID.

        Args:
            session_id: Session ID to look up.

        Returns:
            SessionInfo if found, None otherwise.
        """
        sessions = self.list_sessions()
        for session in sessions:
            if session.session_id == session_id:
                return session
        return None

    def list_sessions(
        self,
        limit: int = 50,
        agent_name: str | None = None,
        project_path: str | None = None,
    ) -> list[SessionInfo]:
        """List recent sessions.

        Args:
            limit: Maximum number of sessions to return.
            agent_name: Filter by agent name.
            project_path: Filter by project path.

        Returns:
            List of SessionInfo, most recent first.
        """
        if not self.history_file.exists():
            return []

        sessions = []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        info = SessionInfo.from_dict(data)

                        # Apply filters
                        if agent_name and info.agent_name != agent_name:
                            continue
                        if project_path and info.project_path != project_path:
                            continue

                        sessions.append(info)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except OSError:
            return []

        # Sort by updated_at descending, return most recent
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions[:limit]

    def get_most_recent_session(
        self,
        agent_name: str | None = None,
        project_path: str | None = None,
    ) -> SessionInfo | None:
        """Get the most recently updated session.

        Args:
            agent_name: Filter by agent name.
            project_path: Filter by project path.

        Returns:
            Most recent SessionInfo or None.
        """
        sessions = self.list_sessions(limit=1, agent_name=agent_name, project_path=project_path)
        return sessions[0] if sessions else None

    def update_session(
        self,
        session_id: str,
        summary: str | None = None,
        message_count: int | None = None,
    ) -> None:
        """Update session metadata.

        Args:
            session_id: Session to update.
            summary: New summary (if provided).
            message_count: New message count (if provided).
        """
        if not self.history_file.exists():
            return

        # Read all sessions
        sessions = []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("session_id") == session_id:
                            # Update fields
                            data["updated_at"] = datetime.now().isoformat()
                            if summary is not None:
                                data["summary"] = summary
                            if message_count is not None:
                                data["message_count"] = message_count
                        sessions.append(data)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return

        # Rewrite file
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                for data in sessions:
                    f.write(json.dumps(data) + "\n")
        except OSError:
            pass

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its data.

        Args:
            session_id: Session to delete.

        Returns:
            True if deleted, False if not found.
        """
        info = self.get_session_info(session_id)
        if not info:
            return False

        # Delete SQLite file
        project_hash = self._get_project_hash(info.project_path)
        db_path = self.sessions_dir / project_hash / f"{session_id}.db"
        if db_path.exists():
            db_path.unlink()

        # Remove from history
        if not self.history_file.exists():
            return False

        sessions = []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("session_id") != session_id:
                            sessions.append(data)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return False

        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                for data in sessions:
                    f.write(json.dumps(data) + "\n")
        except OSError:
            return False

        return True

    def _append_to_history(self, info: SessionInfo) -> None:
        """Append session info to history file."""
        try:
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(info.to_dict()) + "\n")
        except OSError:
            pass


def create_session_manager() -> SessionManager:
    """Create a session manager with default paths.

    Returns:
        Configured SessionManager instance.
    """
    deepagents_dir = Path.home() / ".deepagents"
    deepagents_dir.mkdir(parents=True, exist_ok=True)
    return SessionManager(deepagents_dir=deepagents_dir)
