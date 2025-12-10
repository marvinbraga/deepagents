"""Middleware for the DeepAgent."""

from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.hooks import HooksMiddleware
from deepagents.middleware.mcp import MCPMiddleware
from deepagents.middleware.plan_mode import PlanModeMiddleware
from deepagents.middleware.subagents import CompiledSubAgent, SubAgent, SubAgentMiddleware
from deepagents.middleware.ultrathink import UltrathinkMiddleware, UltrathinkState
from deepagents.middleware.ultrathink_logging import (
    configure_logging as configure_ultrathink_logging,
    get_ultrathink_logger,
)
from deepagents.middleware.user_interaction import (
    UserInteractionMiddleware,
    UserQuestionRequest,
)
from deepagents.middleware.web import (
    WebMiddleware,
    deep_research_async,
    deep_research_sync,
    tavily_search,
    web_fetch_async,
    web_fetch_sync,
    web_search_async,
    web_search_sync,
)

__all__ = [
    "CompiledSubAgent",
    "FilesystemMiddleware",
    "HooksMiddleware",
    "MCPMiddleware",
    "PlanModeMiddleware",
    "SubAgent",
    "SubAgentMiddleware",
    "UltrathinkMiddleware",
    "UltrathinkState",
    "UserInteractionMiddleware",
    "UserQuestionRequest",
    "WebMiddleware",
    "configure_ultrathink_logging",
    "deep_research_async",
    "deep_research_sync",
    "get_ultrathink_logger",
    "tavily_search",
    "web_fetch_async",
    "web_fetch_sync",
    "web_search_async",
    "web_search_sync",
]
