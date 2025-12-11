"""Interactive session picker for resume and delete functionality."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

if TYPE_CHECKING:
    from deepagents_cli.sessions.manager import SessionInfo


# Style themes for different picker modes
RESUME_STYLE = Style.from_dict(
    {
        "header": "#00d7af bold",
        "selected": "#00d7af",
        "selected bold": "#00d7af bold",
        "selected dim": "#00d7af",
        "normal": "#ffffff",
        "dim": "#666666",
    }
)

DELETE_STYLE = Style.from_dict(
    {
        "header": "#ff5f5f bold",
        "selected": "#ff5f5f",
        "selected bold": "#ff5f5f bold",
        "selected dim": "#ff5f5f",
        "normal": "#ffffff",
        "dim": "#666666",
    }
)


class SessionPicker:
    """Interactive picker for selecting a session."""

    def __init__(
        self,
        sessions: list["SessionInfo"],
        title: str = "Resume Previous Session",
        hint: str = "Use ↑↓ to navigate, Enter to select, Esc to cancel",
        style: Style | None = None,
    ) -> None:
        """Initialize the session picker.

        Args:
            sessions: List of sessions to display.
            title: Title to show at the top.
            hint: Help text below title.
            style: Style theme to use.
        """
        self.sessions = sessions
        self.selected_index = 0
        self.result: SessionInfo | None = None
        self.title = title
        self.hint = hint
        self.style = style or RESUME_STYLE

    def _format_time_ago(self, iso_timestamp: str) -> str:
        """Format timestamp as relative time."""
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            now = datetime.now()
            delta = now - dt

            if delta.days > 30:
                return dt.strftime("%Y-%m-%d")
            elif delta.days > 0:
                return f"{delta.days}d ago"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours}h ago"
            elif delta.seconds > 60:
                minutes = delta.seconds // 60
                return f"{minutes}m ago"
            else:
                return "just now"
        except (ValueError, TypeError):
            return "unknown"

    def _get_display_text(self) -> list[tuple[str, str]]:
        """Generate formatted text for display."""
        result = []

        # Header
        result.append(("class:header", f"\n  {self.title}\n"))
        result.append(("class:dim", f"  {self.hint}\n\n"))

        if not self.sessions:
            result.append(("class:dim", "  No previous sessions found.\n"))
            return result

        for i, session in enumerate(self.sessions):
            is_selected = i == self.selected_index

            # Prefix
            if is_selected:
                result.append(("class:selected", "  → "))
            else:
                result.append(("", "    "))

            # Summary (truncated)
            summary = session.summary[:50]
            if len(session.summary) > 50:
                summary += "..."

            if is_selected:
                result.append(("class:selected bold", summary))
            else:
                result.append(("class:normal", summary))

            # Metadata line
            time_ago = self._format_time_ago(session.updated_at)
            branch_info = f" [{session.git_branch}]" if session.git_branch else ""
            meta = f" ({session.message_count} msgs, {time_ago}{branch_info})"

            if is_selected:
                result.append(("class:selected dim", meta))
            else:
                result.append(("class:dim", meta))

            result.append(("", "\n"))

            # Show session ID on second line for selected item
            if is_selected:
                result.append(("class:dim", f"      ID: {session.session_id[:8]}..."))
                result.append(("class:dim", f" | Agent: {session.agent_name}\n"))

        result.append(("", "\n"))
        return result

    async def run_async(self) -> "SessionInfo | None":
        """Run the interactive picker asynchronously.

        Returns:
            Selected SessionInfo or None if cancelled.
        """
        if not self.sessions:
            return None

        # Key bindings
        kb = KeyBindings()

        @kb.add("up")
        @kb.add("k")
        def move_up(event):
            if self.selected_index > 0:
                self.selected_index -= 1

        @kb.add("down")
        @kb.add("j")
        def move_down(event):
            if self.selected_index < len(self.sessions) - 1:
                self.selected_index += 1

        @kb.add("enter")
        def select(event):
            self.result = self.sessions[self.selected_index]
            event.app.exit()

        @kb.add("escape")
        @kb.add("q")
        @kb.add("c-c")
        def cancel(event):
            self.result = None
            event.app.exit()

        # Layout
        layout = Layout(
            HSplit(
                [
                    Window(
                        content=FormattedTextControl(self._get_display_text),
                        wrap_lines=True,
                    )
                ]
            )
        )

        # Application
        app: Application = Application(
            layout=layout,
            key_bindings=kb,
            style=self.style,
            full_screen=False,
            mouse_support=True,
        )

        await app.run_async()
        return self.result

    def run(self) -> "SessionInfo | None":
        """Run the interactive picker (sync version for CLI startup).

        Returns:
            Selected SessionInfo or None if cancelled.
        """
        import asyncio

        # Check if we're in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - this shouldn't be called
            raise RuntimeError("Use run_async() when in async context")
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(self.run_async())


async def pick_session_async(sessions: list["SessionInfo"]) -> "SessionInfo | None":
    """Show interactive session picker for resume (async version).

    Args:
        sessions: List of sessions to choose from.

    Returns:
        Selected session or None if cancelled.
    """
    picker = SessionPicker(
        sessions,
        title="Resume Previous Session",
        hint="Use ↑↓ to navigate, Enter to select, Esc to cancel",
        style=RESUME_STYLE,
    )
    return await picker.run_async()


async def pick_session_for_delete_async(sessions: list["SessionInfo"]) -> "SessionInfo | None":
    """Show interactive session picker for deletion (async version).

    Args:
        sessions: List of sessions to choose from.

    Returns:
        Selected session or None if cancelled.
    """
    picker = SessionPicker(
        sessions,
        title="⚠ Delete Session",
        hint="Use ↑↓ to navigate, Enter to DELETE, Esc to cancel",
        style=DELETE_STYLE,
    )
    return await picker.run_async()


def pick_session(sessions: list["SessionInfo"]) -> "SessionInfo | None":
    """Show interactive session picker (sync version for CLI startup).

    Args:
        sessions: List of sessions to choose from.

    Returns:
        Selected session or None if cancelled.
    """
    picker = SessionPicker(sessions)
    return picker.run()
