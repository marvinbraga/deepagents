This is a Python monorepo for `deepagents`, a LangGraph-based agent harness.

### Project Overview

The project is structured as a monorepo containing three main Python packages:

1.  **`deepagents`**: The core library that provides a flexible and extensible agent framework. It's built on LangGraph and includes features like:
    *   **Plannable Agents:** Agents can create and follow to-do lists.
    *   **Filesystem Access:** Agents can interact with a virtual or real filesystem.
    *   **Sub-agent Delegation:** Agents can delegate tasks to other specialized agents.
    *   **Middleware Architecture:** The agent's capabilities can be extended with custom middleware.
    *   **Pluggable Backends:** The filesystem can be backed by different storage mechanisms (in-memory, disk, etc.).
    *   **Human-in-the-Loop:** Supports interrupting the agent for human approval.

2.  **`deepagents-cli`**: A command-line interface for interacting with `deepagents`. It provides an interactive terminal UI for:
    *   Running agents.
    *   Managing agent memory and skills.
    *   Handling user interactions (questions and confirmations).

3.  **`deepagents-harbor`**: An integration package that connects `deepagents` with "Harbor" and provides LangSmith tracing for observability.

### Building and Running

The project uses `pyproject.toml` for package management. To work with the packages, you'll likely need to install them in editable mode.

**Installation:**

While there isn't a single top-level script for installation, you can likely install the packages individually using `pip`. Since the packages have local path dependencies on each other (as seen in `tool.uv.sources`), you might need to use a tool that understands monorepos like `uv`.

```bash
# TODO: Add specific instructions for setting up the development environment.
# It's likely you'll need to install the packages in editable mode, e.g.:
# pip install -e libs/deepagents
# pip install -e libs/deepagents-cli
# pip install -e libs/harbor
```

**Running the CLI:**

The `deepagents-cli` package provides a command-line script.

```bash
# After installation, you should be able to run the CLI:
deepagents --help
```

**Running Tests:**

Each package has its own set of tests. You can likely run them using `pytest`.

```bash
# TODO: Add specific commands for running tests for each package.
# Example for the deepagents package:
# cd libs/deepagents
# pytest
```

### Development Conventions

*   **Package Management:** The project uses `pyproject.toml` and seems to be moving towards using `uv` for dependency management.
*   **Linting and Formatting:** The project uses `ruff` for linting and formatting, with configurations defined in each package's `pyproject.toml`.
*   **Type Checking:** `mypy` is used for static type checking.
*   **Testing:** `pytest` is the testing framework of choice.
*   **Documentation:** The `README.md` files provide a good starting point for understanding the project. More detailed documentation is available at the provided URLs in the `pyproject.toml` files.
