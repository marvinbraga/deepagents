"""Manual test script for UltrathinkMiddleware."""

import os

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from deepagents.middleware import UltrathinkMiddleware


def test_ultrathink_basic():
    """Test basic ultrathink functionality."""
    print("=" * 60)
    print("Testing UltrathinkMiddleware")
    print("=" * 60)

    # Verify API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    # Create agent with ultrathink enabled by default
    print("\n1. Creating agent with UltrathinkMiddleware...")
    agent = create_agent(
        model=ChatAnthropic(model="claude-sonnet-4-20250514"),
        middleware=[
            UltrathinkMiddleware(
                budget_tokens=5000,
                enabled_by_default=True,
            ),
        ],
    )
    print("   Agent created successfully!")

    # Test with a reasoning task
    print("\n2. Invoking agent with a reasoning task...")
    result = agent.invoke(
        {"messages": [HumanMessage(content="What is 17 * 23? Think step by step.")]}
    )

    print("\n3. Response:")
    last_message = result["messages"][-1]
    print(f"   {last_message.content[:500]}...")

    # Check for thinking blocks in response
    print("\n4. Checking for thinking blocks...")
    for msg in result["messages"]:
        if hasattr(msg, "content") and isinstance(msg.content, list):
            for block in msg.content:
                if isinstance(block, dict) and block.get("type") == "thinking":
                    print("   Found thinking block!")
                    print(f"   Thinking: {block.get('thinking', '')[:200]}...")
                    break

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


def test_ultrathink_tools():
    """Test ultrathink control tools."""
    print("\n" + "=" * 60)
    print("Testing Ultrathink Tools")
    print("=" * 60)

    middleware = UltrathinkMiddleware(budget_tokens=10000)
    tools = middleware.get_tools()

    print(f"\n1. Available tools: {[t.name for t in tools]}")

    for tool in tools:
        print(f"\n   {tool.name}:")
        print(f"   Description: {tool.description[:100]}...")


def test_ultrathink_dynamic():
    """Test dynamic enabling/disabling of ultrathink."""
    print("\n" + "=" * 60)
    print("Testing Dynamic Ultrathink Control")
    print("=" * 60)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    # Create agent with ultrathink disabled by default
    print("\n1. Creating agent with ultrathink disabled by default...")
    agent = create_agent(
        model=ChatAnthropic(model="claude-sonnet-4-20250514"),
        middleware=[
            UltrathinkMiddleware(
                budget_tokens=3000,
                enabled_by_default=False,
            ),
        ],
    )
    print("   Agent created!")

    # Ask agent to enable ultrathink and solve a problem
    print("\n2. Asking agent to enable ultrathink...")
    result = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "First, use the enable_ultrathink tool with budget_tokens=5000. "
                        "Then solve: If a train travels 120 km in 2 hours, what is its average speed?"
                    )
                )
            ]
        }
    )

    print("\n3. Response:")
    for msg in result["messages"]:
        if hasattr(msg, "content"):
            content = str(msg.content)
            if "60" in content or "enabled" in content.lower():
                print(f"   {content[:300]}...")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run tool test (no API call needed)
    test_ultrathink_tools()

    # Uncomment to run tests that require API key:
    # test_ultrathink_basic()
    # test_ultrathink_dynamic()
