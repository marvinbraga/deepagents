"""
Example: Using UserInteractionMiddleware for Interactive Agent Dialogs

This example demonstrates how to use the UserInteractionMiddleware to create
agents that can ask users questions and request confirmations during execution.

The middleware provides two tools:
- ask_user_question: Ask the user a question with optional predefined options
- confirm_action: Request user confirmation before performing an action
"""

import asyncio
from deepagents import create_deep_agent
from deepagents.middleware import UserInteractionMiddleware


async def main():
    # Create an agent with UserInteractionMiddleware
    agent = create_deep_agent(
        model="anthropic:claude-sonnet-4-20250514",
        system_prompt="""You are a helpful assistant that guides users through
        setting up a new project. Always ask for user preferences before making
        decisions, and confirm critical actions before executing them.

        When starting a new project setup:
        1. Ask the user which programming language they prefer
        2. Ask about the project structure they want
        3. Confirm before creating any files
        """,
        middleware=[
            UserInteractionMiddleware(),
        ],
    )

    # Example conversation
    result = await agent.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "Help me set up a new web application project",
            }
        ]
    })

    print("Agent response:", result["messages"][-1].content)


# Example of using the tools directly (for testing/development)
def show_tool_usage():
    """
    Demonstrates the structure of tool calls the agent can make.

    The agent can call ask_user_question like this:
    {
        "question": "Which programming language would you like to use?",
        "options": [
            {"label": "Python", "description": "Best for data science and web backends"},
            {"label": "TypeScript", "description": "Great for full-stack web development"},
            {"label": "Go", "description": "Excellent for high-performance services"}
        ],
        "header": "Language",
        "multi_select": false,
        "allow_other": true
    }

    The agent can call confirm_action like this:
    {
        "action": "Create project directory structure with 15 files",
        "details": "This will create: src/, tests/, docs/, config files, etc.",
        "severity": "medium"
    }

    Severity levels:
    - "low": Routine actions (default color)
    - "medium": Actions that modify state (yellow warning)
    - "high": Critical actions that are hard to undo (red warning)
    """
    pass


if __name__ == "__main__":
    asyncio.run(main())
