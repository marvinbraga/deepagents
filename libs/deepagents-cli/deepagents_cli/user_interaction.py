"""User interaction handlers for asking questions in the terminal UI."""

import sys
import termios
import tty

from rich import box
from rich.panel import Panel

from deepagents_cli.config import console


def prompt_for_user_question(request: dict) -> str | list[str]:
    """Prompt user to answer a question with optional choices.

    Args:
        request: UserQuestionRequest as dict with keys:
            - question: The question text to display
            - options: Optional list of choices
            - header: Optional short label for the panel title
            - descriptions: Optional descriptions for each option
            - multi_select: Whether user can select multiple options
            - allow_custom: Whether to show "Other..." option for custom input
            - default: Default selection (index or string)

    Returns:
        User's response (string for single-select, list[str] for multi-select)
    """
    question = request.get("question", "")
    options = request.get("options")
    header = request.get("header")
    descriptions = request.get("descriptions")
    multi_select = request.get("multi_select", False)
    allow_custom = request.get("allow_custom", True)
    default = request.get("default")

    # Build panel title
    if header:
        title = f"❓ {header}"
    else:
        title = "❓ Agent Question"

    # Display the question in a panel
    console.print(
        Panel(
            f"[bold]{question}[/bold]",
            title=title,
            border_style="blue",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )

    # Handle options or free-form input
    if options:
        return _select_from_options(
            options=options,
            descriptions=descriptions,
            multi_select=multi_select,
            allow_custom=allow_custom,
            default=default,
        )
    else:
        return _get_text_input(default=default)


def _select_from_options(
    options: list[str],
    descriptions: list[str] | None = None,
    multi_select: bool = False,
    allow_custom: bool = True,
    default: str | int | None = None,
) -> str | list[str]:
    """Interactive option selection with arrow key navigation.

    Args:
        options: List of option strings to choose from
        descriptions: Optional descriptions for each option
        multi_select: If True, allow multiple selections with space bar
        allow_custom: If True, add "Other..." option for custom input
        default: Default selection (index or string matching an option)

    Returns:
        Selected option(s) - string for single-select, list for multi-select
    """
    # Add "Other..." option if custom input allowed
    display_options = list(options)
    display_descriptions = list(descriptions) if descriptions else [None] * len(options)

    if allow_custom:
        display_options.append("Other...")
        display_descriptions.append("Enter custom response")

    # Initialize selection state
    selected = set() if multi_select else None
    cursor = 0

    # Set default cursor position
    if isinstance(default, int) and 0 <= default < len(display_options):
        cursor = default
    elif isinstance(default, str) and default in display_options:
        cursor = display_options.index(default)

    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)
            sys.stdout.write("\033[?25l")  # Hide cursor
            sys.stdout.flush()

            first_render = True

            while True:
                if not first_render:
                    # Move cursor back to start of options
                    sys.stdout.write(f"\033[{len(display_options)}A\r")

                first_render = False

                # Render options
                for i, opt in enumerate(display_options):
                    sys.stdout.write("\r\033[K")  # Clear line

                    desc = display_descriptions[i] if i < len(display_descriptions) else None

                    if multi_select:
                        # Multi-select: show checkbox state
                        is_selected = i in selected
                        checkbox = "☑" if is_selected else "☐"
                        highlight = i == cursor

                        if highlight:
                            style = "\033[1;34m"  # Bold blue
                        elif is_selected:
                            style = "\033[32m"  # Green
                        else:
                            style = "\033[2m"  # Dim

                        line = f"{style}{checkbox} {opt}"
                        if desc:
                            line += f"  \033[2m{desc}\033[0m"
                        else:
                            line += "\033[0m"
                    else:
                        # Single select: radio button style
                        is_cursor = i == cursor
                        radio = "●" if is_cursor else "○"

                        if is_cursor:
                            style = "\033[1;34m"  # Bold blue
                        else:
                            style = "\033[2m"  # Dim

                        line = f"{style}{radio} {opt}"
                        if desc:
                            line += f"  \033[2m{desc}\033[0m"
                        else:
                            line += "\033[0m"

                    sys.stdout.write(line + "\n")

                sys.stdout.flush()

                # Read key
                char = sys.stdin.read(1)

                if char == "\x1b":  # ESC sequence
                    next1 = sys.stdin.read(1)
                    next2 = sys.stdin.read(1)
                    if next1 == "[":
                        if next2 == "B":  # Down
                            cursor = (cursor + 1) % len(display_options)
                        elif next2 == "A":  # Up
                            cursor = (cursor - 1) % len(display_options)

                elif char == " " and multi_select:
                    # Toggle selection in multi-select mode
                    if cursor in selected:
                        selected.remove(cursor)
                    else:
                        selected.add(cursor)

                elif char in {"\r", "\n"}:  # Enter
                    sys.stdout.write("\r\n")
                    break

                elif char == "\x03":  # Ctrl+C
                    sys.stdout.write("\r\n")
                    raise KeyboardInterrupt

        finally:
            sys.stdout.write("\033[?25h")  # Show cursor
            sys.stdout.flush()
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    except (termios.error, AttributeError):
        # Fallback for non-Unix systems
        return _fallback_select(display_options, multi_select, default)

    # Handle "Other..." selection
    other_index = len(options)  # Index of "Other..." if added

    if multi_select:
        if other_index in selected and allow_custom:
            selected.remove(other_index)
            custom = input("Enter custom response: ").strip()
            if custom:
                return [display_options[i] for i in sorted(selected) if i < len(options)] + [
                    custom
                ]
        return [display_options[i] for i in sorted(selected) if i < len(options)]
    else:
        if cursor == other_index and allow_custom:
            return input("Enter custom response: ").strip()
        return display_options[cursor]


def _get_text_input(default: str | None = None) -> str:
    """Get free-form text input from user.

    Args:
        default: Optional default value shown to user

    Returns:
        User's input text, or default if Enter pressed with no input
    """
    prompt = "> "
    if default:
        prompt = f"> [{default}] "

    response = input(prompt).strip()
    return response if response else (default or "")


def _fallback_select(
    options: list[str],
    multi_select: bool,
    default: str | int | None,
) -> str | list[str]:
    """Fallback selection for non-Unix systems.

    Uses simple numbered menu input instead of arrow key navigation.

    Args:
        options: List of options to display
        multi_select: Whether to allow multiple selections
        default: Default selection

    Returns:
        Selected option(s)
    """
    print("\nOptions:")
    for i, opt in enumerate(options):
        marker = f"[{i + 1}]"
        print(f"  {marker} {opt}")

    if multi_select:
        print("\nEnter numbers separated by comma (e.g., 1,3):")
        response = input("> ").strip()
        if not response:
            return []
        indices = [int(x.strip()) - 1 for x in response.split(",") if x.strip().isdigit()]
        return [options[i] for i in indices if 0 <= i < len(options)]
    else:
        default_num = default + 1 if isinstance(default, int) else 1
        print(f"\nEnter number (default: {default_num}):")
        response = input("> ").strip()
        if response.isdigit():
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return options[idx]
        # Return default if provided, otherwise first option
        return options[default if isinstance(default, int) and 0 <= default < len(options) else 0]
