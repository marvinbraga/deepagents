"""Middleware for structured user interaction during agent execution."""

from dataclasses import dataclass

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.tools import BaseTool, tool
from langgraph.types import interrupt


@dataclass
class UserQuestionRequest:
    """Request payload for user question interrupt."""

    type: str = "user_question"
    question: str = ""
    options: list[str] | None = None
    header: str | None = None
    descriptions: list[str] | None = None
    multi_select: bool = False
    allow_custom: bool = True
    default: str | int | None = None


USER_INTERACTION_SYSTEM_PROMPT = """## User Interaction Tools

You have access to tools for gathering user input during task execution:

### ask_user_question
Use this tool to ask the user questions when you need:
- Clarification on ambiguous requirements
- User preference between multiple valid approaches
- Confirmation before significant changes
- Custom input (names, values, etc.)

**When to use:**
- Before making architectural decisions
- When requirements are unclear
- When there are trade-offs the user should decide
- Before destructive operations

**When NOT to use:**
- For questions you can reasonably infer the answer to
- For trivial decisions that don't affect the outcome
- Repeatedly for the same type of question
- When the user has already expressed a clear preference

### confirm_action
Use this for explicit confirmation before:
- Deleting files or data
- Making breaking changes
- Operations that are hard to undo
- Actions affecting production systems

Example usage:
```
# Ask for preference
method = ask_user_question(
    question="Which state management approach?",
    options=["Redux", "Zustand", "Context API"],
    descriptions=["Full-featured, more boilerplate", "Minimal, hooks-based", "Built-in, simpler"],
)

# Confirm destructive action
if confirm_action("Delete 23 unused test files"):
    # proceed
```
"""


class UserInteractionMiddleware(AgentMiddleware):
    """Middleware for structured user interaction during agent execution.

    This middleware provides tools for the agent to ask questions,
    request confirmations, and gather user input in a structured way.

    Example:
        ```python
        from deepagents import create_deep_agent
        from deepagents.middleware.user_interaction import UserInteractionMiddleware

        agent = create_deep_agent(
            middleware=[UserInteractionMiddleware()],
        )
        ```
    """

    def __init__(self) -> None:
        """Initialize the user interaction middleware."""
        self._tools: list[BaseTool] = []

    def get_tools(self) -> list[BaseTool]:
        """Get user interaction tools.

        Returns:
            List of tools for user interaction: ask_user_question and confirm_action.
        """
        if self._tools:
            return self._tools

        @tool
        def ask_user_question(
            question: str,
            options: list[str] | None = None,
            header: str | None = None,
            descriptions: list[str] | None = None,
            multi_select: bool = False,
            allow_custom: bool = True,
            default: str | int | None = None,
        ) -> str | list[str]:
            """Ask the user a question and wait for their response.

            Use this tool when you need to:
            - Clarify ambiguous requirements
            - Present implementation choices
            - Confirm understanding before proceeding
            - Get user preferences or decisions

            Args:
                question: The question to ask the user. Should be clear and specific.
                options: Optional list of choices. If provided, user selects from these.
                         If None, user provides free-form text input.
                header: Short label for the question (max 12 chars). Used in compact display.
                descriptions: Optional descriptions for each option (same length as options).
                multi_select: If True, user can select multiple options. Default False.
                allow_custom: If True and options provided, user can enter custom text.
                default: Default option (index or text). Used if user presses Enter.

            Returns:
                User's response. String for single-select, list[str] for multi-select.

            Examples:
                # Simple yes/no question
                answer = ask_user_question(
                    question="Should I proceed with the refactoring?",
                    options=["Yes", "No"],
                )

                # Multiple choice with descriptions
                choice = ask_user_question(
                    question="Which authentication method?",
                    header="Auth",
                    options=["JWT", "Session", "OAuth2"],
                    descriptions=[
                        "Stateless tokens, good for APIs",
                        "Server-side sessions, simpler setup",
                        "Third-party providers like Google/GitHub"
                    ],
                )

                # Free-form input
                name = ask_user_question(
                    question="What should we name the new component?",
                )

                # Multi-select
                features = ask_user_question(
                    question="Which features should we include?",
                    options=["Dark mode", "Notifications", "Export", "Search"],
                    multi_select=True,
                )
            """
            # Validate inputs
            if options and descriptions:
                if len(options) != len(descriptions):
                    raise ValueError("options and descriptions must have same length")

            # Truncate header if too long
            if header and len(header) > 12:
                header = header[:12]

            # Create interrupt request
            request = UserQuestionRequest(
                question=question,
                options=options,
                header=header,
                descriptions=descriptions,
                multi_select=multi_select,
                allow_custom=allow_custom,
                default=default,
            )

            # Pause execution and wait for user response
            response = interrupt(request.__dict__)

            return response

        @tool
        def confirm_action(
            action: str,
            details: str | None = None,
            default: bool = True,
        ) -> bool:
            """Ask user to confirm before proceeding with an action.

            Use this for potentially destructive or significant operations
            where you want explicit user consent.

            Args:
                action: Brief description of what will happen
                details: Optional additional context
                default: Default response if user just presses Enter

            Returns:
                True if user confirms, False otherwise

            Example:
                if confirm_action(
                    action="Delete 15 test files",
                    details="Files matching *_test.py in /src/tests/"
                ):
                    # proceed with deletion
            """
            request = UserQuestionRequest(
                type="confirm_action",
                question=f"Confirm: {action}",
                options=["Yes, proceed", "No, cancel"],
                descriptions=[details, None] if details else None,
                default=0 if default else 1,
            )

            response = interrupt(request.__dict__)
            return response in ("Yes, proceed", "yes", "y", True)

        self._tools = [ask_user_question, confirm_action]
        return self._tools

    def get_system_prompt_addition(self) -> str:
        """Get the system prompt addition for user interaction tools.

        Returns:
            System prompt text explaining when and how to use the tools.
        """
        return USER_INTERACTION_SYSTEM_PROMPT

    @property
    def tools(self) -> list[BaseTool]:
        """Get user interaction tools.

        Returns:
            List of tools for user interaction.
        """
        return self.get_tools()
