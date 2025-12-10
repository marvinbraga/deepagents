"""Command handlers for slash commands and bash execution."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import InMemorySaver

from .config import COLORS, DEEP_AGENTS_ASCII, console, settings
from .plan.commands import register_plan_commands
from .ui import TokenTracker, show_interactive_help

if TYPE_CHECKING:
    from .custom_commands import CommandRegistry

# Register plan commands
PLAN_COMMANDS = register_plan_commands()

# Project analysis functions for /init command


def _detect_project_type(project_root: Path) -> dict:
    """Analyze project to detect language, framework, and configuration.

    Returns a dict with detected information about the project.
    """
    info = {
        "languages": [],
        "frameworks": [],
        "package_manager": None,
        "test_command": None,
        "build_command": None,
        "run_command": None,
        "lint_command": None,
        "key_files": [],
        "directories": [],
        "description": None,
        "name": project_root.name,
    }

    # Detect Python projects
    pyproject = project_root / "pyproject.toml"
    setup_py = project_root / "setup.py"
    requirements = project_root / "requirements.txt"

    if pyproject.exists():
        info["languages"].append("Python")
        info["key_files"].append("pyproject.toml")
        info["package_manager"] = "uv/pip"

        # Parse pyproject.toml for more details
        try:
            content = pyproject.read_text()
            if "[tool.poetry]" in content:
                info["package_manager"] = "poetry"
                info["build_command"] = "poetry build"
            elif "[build-system]" in content:
                info["build_command"] = "python -m build"

            # Extract project name and description
            import re

            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if name_match:
                info["name"] = name_match.group(1)

            desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
            if desc_match:
                info["description"] = desc_match.group(1)

            # Detect test framework
            if "pytest" in content:
                info["test_command"] = "pytest"
            elif "unittest" in content:
                info["test_command"] = "python -m unittest"

            # Detect linters
            if "[tool.ruff]" in content:
                info["lint_command"] = "ruff check ."
            elif "[tool.black]" in content or "[tool.isort]" in content:
                info["lint_command"] = "black . && isort ."

            # Detect frameworks
            if "fastapi" in content.lower():
                info["frameworks"].append("FastAPI")
            if "django" in content.lower():
                info["frameworks"].append("Django")
            if "flask" in content.lower():
                info["frameworks"].append("Flask")
            if "langchain" in content.lower():
                info["frameworks"].append("LangChain")

        except (OSError, UnicodeDecodeError):
            pass

    elif setup_py.exists():
        info["languages"].append("Python")
        info["key_files"].append("setup.py")
        info["package_manager"] = "pip"
        info["build_command"] = "python setup.py build"

    elif requirements.exists():
        info["languages"].append("Python")
        info["key_files"].append("requirements.txt")
        info["package_manager"] = "pip"

    # Detect Node.js projects
    package_json = project_root / "package.json"
    if package_json.exists():
        info["languages"].append("JavaScript/TypeScript")
        info["key_files"].append("package.json")

        # Check for package manager lock files
        if (project_root / "pnpm-lock.yaml").exists():
            info["package_manager"] = "pnpm"
        elif (project_root / "yarn.lock").exists():
            info["package_manager"] = "yarn"
        elif (project_root / "package-lock.json").exists():
            info["package_manager"] = "npm"
        else:
            info["package_manager"] = "npm"

        try:
            import json

            pkg = json.loads(package_json.read_text())
            info["name"] = pkg.get("name", info["name"])
            info["description"] = pkg.get("description")

            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                info["test_command"] = f"{info['package_manager']} test"
            if "build" in scripts:
                info["build_command"] = f"{info['package_manager']} run build"
            if "dev" in scripts:
                info["run_command"] = f"{info['package_manager']} run dev"
            elif "start" in scripts:
                info["run_command"] = f"{info['package_manager']} start"
            if "lint" in scripts:
                info["lint_command"] = f"{info['package_manager']} run lint"

            # Detect frameworks from dependencies
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                info["frameworks"].append("Next.js")
            if "react" in deps:
                info["frameworks"].append("React")
            if "vue" in deps:
                info["frameworks"].append("Vue.js")
            if "express" in deps:
                info["frameworks"].append("Express")
            if "typescript" in deps:
                if "TypeScript" not in info["languages"]:
                    info["languages"] = ["TypeScript"]

        except (OSError, json.JSONDecodeError):
            pass

    # Detect Rust projects
    cargo_toml = project_root / "Cargo.toml"
    if cargo_toml.exists():
        info["languages"].append("Rust")
        info["key_files"].append("Cargo.toml")
        info["package_manager"] = "cargo"
        info["build_command"] = "cargo build"
        info["test_command"] = "cargo test"
        info["run_command"] = "cargo run"

        try:
            content = cargo_toml.read_text()
            import re

            name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
            if name_match:
                info["name"] = name_match.group(1)
            desc_match = re.search(r'description\s*=\s*"([^"]+)"', content)
            if desc_match:
                info["description"] = desc_match.group(1)
        except (OSError, UnicodeDecodeError):
            pass

    # Detect Go projects
    go_mod = project_root / "go.mod"
    if go_mod.exists():
        info["languages"].append("Go")
        info["key_files"].append("go.mod")
        info["package_manager"] = "go modules"
        info["build_command"] = "go build"
        info["test_command"] = "go test ./..."
        info["run_command"] = "go run ."

    # Detect common directories
    common_dirs = [
        ("src", "Source code"),
        ("lib", "Library code"),
        ("app", "Application code"),
        ("apps", "Applications"),
        ("pkg", "Packages"),
        ("cmd", "Command entry points"),
        ("internal", "Internal packages"),
        ("tests", "Test files"),
        ("test", "Test files"),
        ("docs", "Documentation"),
        ("scripts", "Utility scripts"),
        ("config", "Configuration"),
        ("public", "Public assets"),
        ("static", "Static files"),
        ("templates", "Template files"),
        ("migrations", "Database migrations"),
    ]

    for dir_name, description in common_dirs:
        dir_path = project_root / dir_name
        if dir_path.is_dir():
            info["directories"].append((dir_name, description))

    # Detect common key files
    common_files = [
        "README.md",
        "README.rst",
        "README.txt",
        "CONTRIBUTING.md",
        "LICENSE",
        "Makefile",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".env.example",
        "Taskfile.yml",
        "justfile",
    ]

    for filename in common_files:
        if (project_root / filename).exists():
            info["key_files"].append(filename)

    # Detect Makefile commands
    makefile = project_root / "Makefile"
    if makefile.exists():
        try:
            content = makefile.read_text()
            if not info["test_command"] and "test:" in content:
                info["test_command"] = "make test"
            if not info["build_command"] and "build:" in content:
                info["build_command"] = "make build"
            if not info["lint_command"] and "lint:" in content:
                info["lint_command"] = "make lint"
            if not info["run_command"] and "run:" in content:
                info["run_command"] = "make run"
        except (OSError, UnicodeDecodeError):
            pass

    # Try to get description from README
    if not info["description"]:
        for readme in ["README.md", "README.rst", "README.txt"]:
            readme_path = project_root / readme
            if readme_path.exists():
                try:
                    content = readme_path.read_text()
                    # Get first non-empty, non-header line
                    lines = content.split("\n")
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#") and not line.startswith("="):
                            info["description"] = line[:150]
                            break
                except (OSError, UnicodeDecodeError):
                    pass
                break

    # Check for monorepo structure (libs/, packages/, etc.)
    monorepo_dirs = ["libs", "packages", "modules", "projects"]
    subprojects = []
    for mono_dir in monorepo_dirs:
        mono_path = project_root / mono_dir
        if mono_path.is_dir():
            for subdir in mono_path.iterdir():
                if subdir.is_dir():
                    # Check if subdir has its own project file
                    if (subdir / "pyproject.toml").exists():
                        subprojects.append((subdir.name, "Python"))
                    elif (subdir / "package.json").exists():
                        subprojects.append((subdir.name, "JavaScript/TypeScript"))
                    elif (subdir / "Cargo.toml").exists():
                        subprojects.append((subdir.name, "Rust"))
                    elif (subdir / "go.mod").exists():
                        subprojects.append((subdir.name, "Go"))

    if subprojects:
        info["is_monorepo"] = True
        info["subprojects"] = subprojects
        # Infer languages from subprojects if not already detected
        if not info["languages"] or info["languages"] == ["Unknown"]:
            langs = list(set(lang for _, lang in subprojects))
            if langs:
                info["languages"] = langs

    # Fallback defaults
    if not info["languages"]:
        info["languages"] = ["Unknown"]

    if not info["test_command"]:
        if "Python" in info["languages"]:
            info["test_command"] = "pytest"

    return info


def _generate_agent_md_content(project_root: Path) -> str:
    """Generate agent.md content by analyzing the project."""
    info = _detect_project_type(project_root)

    # Build the content
    sections = []

    # Header
    sections.append(f"# {info['name']}")
    sections.append("")

    # Description
    if info["description"]:
        sections.append(info["description"])
        sections.append("")

    # Project type summary
    lang_str = ", ".join(info["languages"])
    framework_str = ", ".join(info["frameworks"]) if info["frameworks"] else "None detected"
    sections.append("## Project Type")
    sections.append("")
    if info.get("is_monorepo"):
        sections.append("- **Type:** Monorepo")
    sections.append(f"- **Language(s):** {lang_str}")
    sections.append(f"- **Framework(s):** {framework_str}")
    if info["package_manager"]:
        sections.append(f"- **Package Manager:** {info['package_manager']}")
    sections.append("")

    # Monorepo subprojects
    if info.get("subprojects"):
        sections.append("## Subprojects")
        sections.append("")
        for name, lang in info["subprojects"]:
            sections.append(f"- `{name}` ({lang})")
        sections.append("")

    # Directory structure
    if info["directories"]:
        sections.append("## Directory Structure")
        sections.append("")
        for dir_name, description in info["directories"]:
            sections.append(f"- `{dir_name}/` - {description}")
        sections.append("")

    # Key files
    if info["key_files"]:
        sections.append("## Key Files")
        sections.append("")
        for filename in info["key_files"]:
            sections.append(f"- `{filename}`")
        sections.append("")

    # Development commands
    commands_added = False
    commands_section = ["## Development Commands", ""]

    if info["run_command"]:
        commands_section.append(f"- **Run:** `{info['run_command']}`")
        commands_added = True
    if info["build_command"]:
        commands_section.append(f"- **Build:** `{info['build_command']}`")
        commands_added = True
    if info["test_command"]:
        commands_section.append(f"- **Test:** `{info['test_command']}`")
        commands_added = True
    if info["lint_command"]:
        commands_section.append(f"- **Lint:** `{info['lint_command']}`")
        commands_added = True

    if commands_added:
        sections.extend(commands_section)
        sections.append("")

    # Coding conventions placeholder
    sections.append("## Coding Conventions")
    sections.append("")
    sections.append("<!-- Add project-specific coding conventions here -->")
    sections.append("- Follow existing code style and patterns")
    sections.append("- Write clear, descriptive commit messages")
    sections.append("- Add tests for new features")
    sections.append("")

    # Notes section
    sections.append("## Notes")
    sections.append("")
    sections.append("<!-- Add any additional notes or context for the AI assistant -->")
    sections.append("")

    return "\n".join(sections)


def _collect_project_context(project_root: Path, max_files: int = 15) -> str:
    """Collect relevant project files content for LLM analysis.

    Args:
        project_root: Path to the project root.
        max_files: Maximum number of files to include.

    Returns:
        String with file contents formatted for LLM context.
    """
    context_parts = []

    # Priority files to read (in order)
    priority_files = [
        "README.md",
        "README.rst",
        "README.txt",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "setup.py",
        "setup.cfg",
        "Makefile",
        "justfile",
        "Taskfile.yml",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Dockerfile",
        ".env.example",
        "CONTRIBUTING.md",
        "ARCHITECTURE.md",
    ]

    files_read = 0
    for filename in priority_files:
        if files_read >= max_files:
            break

        filepath = project_root / filename
        if filepath.exists() and filepath.is_file():
            try:
                content = filepath.read_text(errors="ignore")
                # Limit file size to avoid token overflow
                if len(content) > 8000:
                    content = content[:8000] + "\n... (truncated)"
                context_parts.append(f"### {filename}\n```\n{content}\n```\n")
                files_read += 1
            except (OSError, UnicodeDecodeError):
                pass

    # Also include directory structure
    try:
        dirs = []
        files = []
        for item in sorted(project_root.iterdir()):
            if item.name.startswith(".") and item.name not in [".env.example"]:
                continue
            if item.is_dir():
                # Check if it has content
                try:
                    subcount = len(list(item.iterdir())[:5])
                    dirs.append(f"  {item.name}/ ({subcount}+ items)")
                except (OSError, PermissionError):
                    dirs.append(f"  {item.name}/")
            else:
                files.append(f"  {item.name}")

        structure = "### Directory Structure\n```\n"
        structure += "\n".join(dirs[:20])  # Limit dirs
        if len(dirs) > 20:
            structure += f"\n  ... and {len(dirs) - 20} more directories"
        structure += "\n" + "\n".join(files[:15])  # Limit files
        if len(files) > 15:
            structure += f"\n  ... and {len(files) - 15} more files"
        structure += "\n```\n"
        context_parts.insert(0, structure)
    except (OSError, PermissionError):
        pass

    return "\n".join(context_parts)


INIT_LLM_PROMPT = '''You are analyzing a software project to create a configuration file for an AI coding assistant.

Based on the project information below, generate a comprehensive `agent.md` file in Markdown format.

The file should include:

1. **Project name and brief description** (1-2 sentences)
2. **Project Type** section with:
   - Primary language(s)
   - Framework(s) used
   - Package manager
   - Whether it's a monorepo (if applicable)
3. **Architecture Overview** - Brief description of the project structure and key components
4. **Directory Structure** - Important directories and their purposes
5. **Key Files** - Important files developers should know about
6. **Development Commands** - How to run, test, build, and lint the project
7. **Coding Conventions** - Code style, patterns, and best practices used in this project
8. **Important Notes** - Any other important information for an AI assistant working on this codebase

Be specific and accurate based on what you see in the project files. Don't make assumptions about things not shown.
Keep the content concise but informative. Use bullet points where appropriate.

PROJECT INFORMATION:
{project_context}

Generate the agent.md content now (in Markdown format, starting with # Project Name):'''


async def _generate_agent_md_with_llm(project_root: Path) -> str | None:
    """Use LLM to generate agent.md content by analyzing the project.

    Args:
        project_root: Path to the project root.

    Returns:
        Generated content string, or None if LLM generation fails.
    """
    from langchain_core.messages import HumanMessage

    try:
        from deepagents_cli.models import create_model

        model = create_model()
    except Exception as e:
        console.print(f"[yellow]Could not initialize model: {e}[/yellow]")
        return None

    # Collect project context
    project_context = _collect_project_context(project_root)

    if not project_context.strip():
        return None

    # Add basic detection info
    info = _detect_project_type(project_root)
    detection_summary = f"""
### Auto-detected Information
- Project name: {info['name']}
- Languages: {', '.join(info['languages'])}
- Frameworks: {', '.join(info['frameworks']) if info['frameworks'] else 'None detected'}
- Package manager: {info['package_manager'] or 'Unknown'}
- Test command: {info['test_command'] or 'Unknown'}
- Build command: {info['build_command'] or 'Unknown'}
- Lint command: {info['lint_command'] or 'Unknown'}
"""
    if info.get("subprojects"):
        detection_summary += f"- Subprojects: {', '.join(name for name, _ in info['subprojects'])}\n"

    full_context = detection_summary + "\n" + project_context

    # Call LLM
    prompt = INIT_LLM_PROMPT.format(project_context=full_context)

    try:
        response = await model.ainvoke([HumanMessage(content=prompt)])
        content = response.content

        # Clean up response if needed
        if isinstance(content, str):
            # Remove any markdown code block wrapper if present
            content = content.strip()
            if content.startswith("```markdown"):
                content = content[11:]
            elif content.startswith("```md"):
                content = content[5:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return content.strip()

        return None
    except Exception as e:
        console.print(f"[yellow]LLM generation failed: {e}[/yellow]")
        return None


async def _handle_init_command_async() -> bool:
    """Handle /init command to create project agent.md file using LLM.

    Analyzes the project structure using LLM and creates a .deepagents/agent.md file
    with comprehensive information about the project.

    Returns:
        True when handled.
    """
    console.print()

    # Determine project root or use cwd
    project_root = settings.project_root or Path.cwd()

    # Create .deepagents directory path
    deepagents_dir = project_root / ".deepagents"
    agent_md_path = deepagents_dir / "agent.md"

    # Check if agent.md already exists (in either location)
    existing_paths = []
    if agent_md_path.exists():
        existing_paths.append(str(agent_md_path))
    alt_path = project_root / "agent.md"
    if alt_path.exists():
        existing_paths.append(str(alt_path))

    if existing_paths:
        console.print("[yellow]⚠ agent.md already exists:[/yellow]")
        for p in existing_paths:
            console.print(f"  [dim]{p}[/dim]")
        console.print()
        console.print("[dim]To reinitialize, delete the existing file(s) first.[/dim]")
        console.print()
        return True

    try:
        # Create .deepagents directory if it doesn't exist
        deepagents_dir.mkdir(parents=True, exist_ok=True)

        # Try LLM generation first
        console.print("[dim]Analyzing project with AI...[/dim]")

        content = await _generate_agent_md_with_llm(project_root)

        if not content:
            # Fallback to static generation
            console.print("[dim]Falling back to static analysis...[/dim]")
            content = _generate_agent_md_content(project_root)

        # Write the file
        agent_md_path.write_text(content)

        console.print("[green]✓ Created project configuration:[/green]")
        console.print(f"  [cyan]{agent_md_path}[/cyan]")
        console.print()

        console.print("[dim]The AI assistant will use this file to understand your project.[/dim]")
        console.print("[dim]Feel free to edit it to add more context or correct any details.[/dim]")
        console.print()

        # Add to .gitignore suggestion
        gitignore_path = project_root / ".gitignore"
        if gitignore_path.exists():
            try:
                gitignore_content = gitignore_path.read_text()
                if ".deepagents/" not in gitignore_content:
                    console.print(
                        "[dim]💡 Tip: Consider adding '.deepagents/' to .gitignore "
                        "if you don't want to share your agent config.[/dim]"
                    )
                    console.print()
            except (OSError, UnicodeDecodeError):
                pass

    except OSError as e:
        console.print(f"[red]✗ Failed to create agent.md: {e}[/red]")
        console.print()

    return True


def _handle_init_command() -> bool:
    """Synchronous wrapper for _handle_init_command_async.

    This is needed because handle_command may call this synchronously.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # If we're already in an async context, create a task
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _handle_init_command_async())
            return future.result()
    except RuntimeError:
        # No running loop, we can use asyncio.run directly
        return asyncio.run(_handle_init_command_async())


async def _handle_delete_session_async(args: list[str]) -> bool:
    """Handle /delete command to remove a session (async version).

    Args:
        args: Command arguments (session ID prefix or search term, or empty for picker).

    Returns:
        True when handled.
    """
    from deepagents_cli.sessions import create_session_manager
    from deepagents_cli.sessions.picker import pick_session_for_delete_async

    sm = create_session_manager()
    sessions = sm.list_sessions(limit=50)

    if not sessions:
        console.print()
        console.print("[yellow]No sessions found.[/yellow]")
        console.print()
        return True

    target_session = None

    # If no args, show interactive picker
    if not args:
        target_session = await pick_session_for_delete_async(sessions)
        if not target_session:
            console.print("[dim]No session selected.[/dim]")
            console.print()
            return True
    else:
        # Try to match by ID prefix or summary
        search_term = " ".join(args).lower()

        # First try matching by ID prefix
        for session in sessions:
            if session.session_id.lower().startswith(search_term):
                target_session = session
                break

        # Then try matching by summary content
        if not target_session:
            for session in sessions:
                if search_term in session.summary.lower():
                    target_session = session
                    break

        if not target_session:
            console.print()
            console.print(f"[yellow]No session found matching: {search_term}[/yellow]")
            console.print("[dim]Type /sessions to list, or /delete for picker.[/dim]")
            console.print()
            return True

    # Delete the session
    console.print()
    console.print(f"[red]Deleting session:[/red] {target_session.summary[:50]}...")
    console.print(f"[dim]  ID: {target_session.session_id[:8]}...[/dim]")

    if sm.delete_session(target_session.session_id):
        console.print("[green]✓ Session deleted successfully.[/green]")
    else:
        console.print("[red]✗ Failed to delete session.[/red]")

    console.print()
    return True


async def _handle_resume_command_async(args: list[str]) -> tuple[str, str] | bool:
    """Handle /resume command with optional session ID or picker (async version).

    Args:
        args: Command arguments (session ID prefix or empty for picker).

    Returns:
        - ("resume", session_id) to signal session switch
        - True if handled without switching
    """
    from deepagents_cli.sessions import create_session_manager
    from deepagents_cli.sessions.picker import pick_session_async

    sm = create_session_manager()
    sessions = sm.list_sessions(limit=20)

    if not sessions:
        console.print()
        console.print("[yellow]No previous sessions found.[/yellow]")
        console.print()
        return True

    # If no args, show interactive picker
    if not args:
        selected = await pick_session_async(sessions)
        if selected:
            return ("resume", selected.session_id)
        console.print("[dim]No session selected.[/dim]")
        console.print()
        return True

    # Try to match session by ID prefix or summary
    search_term = " ".join(args).lower()

    # First try matching by ID prefix
    for session in sessions:
        if session.session_id.lower().startswith(search_term):
            return ("resume", session.session_id)

    # Then try matching by summary content
    for session in sessions:
        if search_term in session.summary.lower():
            return ("resume", session.session_id)

    console.print()
    console.print(f"[yellow]No session found matching: {search_term}[/yellow]")
    console.print("[dim]Type /sessions to list available sessions.[/dim]")
    console.print()
    return True


def _show_sessions_list() -> None:
    """Show list of recent sessions."""
    from deepagents_cli.sessions import create_session_manager

    console.print()
    console.print("[bold cyan]Recent Sessions[/bold cyan]")
    console.print()

    sm = create_session_manager()
    sessions = sm.list_sessions(limit=10)

    if not sessions:
        console.print("[dim]No previous sessions found.[/dim]")
        console.print()
        return

    for i, session in enumerate(sessions):
        # Format time ago
        from datetime import datetime

        try:
            dt = datetime.fromisoformat(session.updated_at)
            now = datetime.now()
            delta = now - dt
            if delta.days > 0:
                time_ago = f"{delta.days}d ago"
            elif delta.seconds > 3600:
                time_ago = f"{delta.seconds // 3600}h ago"
            elif delta.seconds > 60:
                time_ago = f"{delta.seconds // 60}m ago"
            else:
                time_ago = "just now"
        except (ValueError, TypeError):
            time_ago = "unknown"

        # Truncate summary
        summary = session.summary[:45]
        if len(session.summary) > 45:
            summary += "..."

        # Show session info
        prefix = "→ " if i == 0 else "  "
        console.print(
            f"{prefix}[cyan]{session.session_id[:8]}[/cyan] "
            f"{summary} [dim]({session.message_count} msgs, {time_ago})[/dim]"
        )

    console.print()
    console.print("[dim]To resume: deepagents --resume {session_id}[/dim]")
    console.print("[dim]Or use: deepagents --resume (interactive picker)[/dim]")
    console.print()


async def handle_command(
    command: str,
    agent,
    token_tracker: TokenTracker,
    command_registry: "CommandRegistry | None" = None,
) -> str | bool | tuple[str, str] | tuple[bool, str]:
    """Handle slash commands.

    Args:
        command: The command string (with leading slash).
        agent: The agent instance.
        token_tracker: Token usage tracker.
        command_registry: Optional registry for custom commands.

    Returns:
        - 'exit' to exit the CLI
        - True if command was handled (no further action needed)
        - False to pass to agent (not used currently)
        - (True, prompt) for custom commands that expand to a prompt
        - ("resume", session_id) to switch sessions
    """
    from .custom_commands import handle_custom_command, parse_command_line

    # Parse command and arguments
    cmd_name, cmd_args = parse_command_line(command)

    # Built-in commands (highest priority)
    if cmd_name in ["quit", "exit", "q"]:
        return "exit"

    if cmd_name == "clear":
        # Reset agent conversation state
        agent.checkpointer = InMemorySaver()

        # Reset token tracking to baseline
        token_tracker.reset()

        # Clear screen and show fresh UI
        console.clear()
        console.print(DEEP_AGENTS_ASCII, style=f"bold {COLORS['primary']}")
        console.print()
        console.print(
            "... Fresh start! Screen cleared and conversation reset.", style=COLORS["agent"]
        )
        console.print()
        return True

    if cmd_name == "init":
        return await _handle_init_command_async()

    if cmd_name == "help":
        show_interactive_help(command_registry=command_registry)
        return True

    if cmd_name == "tokens":
        token_tracker.display_session()
        return True

    if cmd_name == "resume":
        return await _handle_resume_command_async(cmd_args)

    if cmd_name == "sessions":
        _show_sessions_list()
        return True

    if cmd_name == "delete":
        return await _handle_delete_session_async(cmd_args)

    # Check plan commands
    if cmd_name in PLAN_COMMANDS:
        handler = PLAN_COMMANDS[cmd_name]
        return handler(agent, console)

    # Check custom commands
    if command_registry:
        handled, expanded_prompt = handle_custom_command(
            command_name=cmd_name,
            args=cmd_args,
            registry=command_registry,
            console=console,
            project_root=str(settings.project_root) if settings.project_root else None,
            cwd=str(Path.cwd()),
        )
        if handled:
            if expanded_prompt:
                return (True, expanded_prompt)
            return True

    console.print()
    console.print(f"[yellow]Unknown command: /{cmd_name}[/yellow]")
    console.print("[dim]Type /help for available commands.[/dim]")
    console.print()
    return True


def execute_bash_command(command: str) -> bool:
    """Execute a bash command and display output. Returns True if handled."""
    cmd = command.strip().lstrip("!")

    if not cmd:
        return True

    try:
        console.print()
        console.print(f"[dim]$ {cmd}[/dim]")

        # Execute the command
        result = subprocess.run(
            cmd, check=False, shell=True, capture_output=True, text=True, timeout=30, cwd=Path.cwd()
        )

        # Display output
        if result.stdout:
            console.print(result.stdout, style=COLORS["dim"], markup=False)
        if result.stderr:
            console.print(result.stderr, style="red", markup=False)

        # Show return code if non-zero
        if result.returncode != 0:
            console.print(f"[dim]Exit code: {result.returncode}[/dim]")

        console.print()
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out after 30 seconds[/red]")
        console.print()
        return True
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/red]")
        console.print()
        return True
