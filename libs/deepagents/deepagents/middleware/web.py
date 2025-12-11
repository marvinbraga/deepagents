"""Web search and research middleware for DeepAgents.

This middleware provides web search capabilities using DuckDuckGo (no API key required)
and deep research functionality that uses LLM to synthesize information from multiple sources.
"""

from __future__ import annotations

import asyncio
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.tools import BaseTool, tool
from loguru import logger

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

# Type aliases
RegionType = Literal[
    "wt-wt",  # Worldwide
    "us-en",  # United States
    "uk-en",  # United Kingdom
    "br-pt",  # Brazil
    "de-de",  # Germany
    "fr-fr",  # France
    "es-es",  # Spain
    "it-it",  # Italy
    "jp-jp",  # Japan
    "kr-kr",  # Korea
    "cn-zh",  # China
    "ru-ru",  # Russia
]

SafeSearchType = Literal["on", "moderate", "off"]
TimeLimitType = Literal["d", "w", "m", "y"] | None  # day, week, month, year


# =============================================================================
# System Prompts
# =============================================================================

WEB_SEARCH_SYSTEM_PROMPT = """# Web Search Tools

You have access to web search tools that allow you to search the internet for current information.

## Available Tools

### web_search
Search the web using DuckDuckGo. No API key required.
- Use for finding current information, news, documentation, etc.
- Returns titles, URLs, and snippets from search results.
- Supports region filtering and time limits.

### web_fetch
Fetch and extract content from a specific URL.
- Use when you need the full content of a page found via search.
- Automatically extracts main text content from HTML.
- Handles common errors gracefully.

## Best Practices

1. **Search first, then fetch**: Use web_search to find relevant URLs, then web_fetch for detailed content.
2. **Be specific**: Use detailed search queries for better results.
3. **Use time limits**: For recent information, use timelimit='d' (day), 'w' (week), or 'm' (month).
4. **Cite sources**: Always mention the source URL when using information from web searches.
"""

DEEP_RESEARCH_SYSTEM_PROMPT = """# Deep Research Tool

You have access to a deep_research tool that performs comprehensive web research.

## How It Works

1. Searches multiple queries related to your topic
2. Fetches content from the most relevant pages
3. Synthesizes information using an LLM
4. Returns a comprehensive research report

## When to Use

- Complex questions requiring multiple sources
- Topics needing current, up-to-date information
- Research tasks where synthesis is valuable
- When you need a comprehensive overview of a subject

## Best Practices

1. **Clear objectives**: Provide specific research questions
2. **Context matters**: Include relevant context in your query
3. **Review sources**: The tool returns source URLs - verify important claims
"""


# =============================================================================
# Tool Descriptions
# =============================================================================

WEB_SEARCH_TOOL_DESCRIPTION = """Search the web using DuckDuckGo (no API key required).

Returns a list of search results with titles, URLs, and snippets.

Args:
    query: The search query string.
    max_results: Maximum number of results to return (default: 5, max: 20).
    region: Region for search results (default: "wt-wt" for worldwide).
            Options: "us-en", "uk-en", "br-pt", "de-de", "fr-fr", etc.
    timelimit: Filter by time - "d" (day), "w" (week), "m" (month), "y" (year).
    safesearch: Safe search level - "on", "moderate" (default), "off".

Returns:
    List of dicts with keys: title, href, body (snippet).

Example:
    results = web_search("Python async best practices 2025", max_results=5)
"""

WEB_FETCH_TOOL_DESCRIPTION = """Fetch and extract content from a URL.

Retrieves the page content and extracts the main text, removing HTML tags,
scripts, styles, and other non-content elements.

Args:
    url: The URL to fetch content from.
    timeout: Request timeout in seconds (default: 10).

Returns:
    Dict with keys: url, title, content, error (if any).

Example:
    page = web_fetch("https://docs.python.org/3/library/asyncio.html")
"""

DEEP_RESEARCH_TOOL_DESCRIPTION = """Perform deep web research on a topic.

This tool:
1. Generates multiple search queries for comprehensive coverage
2. Searches the web for each query
3. Fetches content from the most relevant pages
4. Synthesizes all information into a coherent research report

Args:
    query: The research question or topic.
    num_searches: Number of search queries to generate (default: 3, max: 5).
    results_per_search: Results to fetch per search (default: 3, max: 5).
    include_sources: Include source URLs in the report (default: True).

Returns:
    A comprehensive research report synthesized from multiple sources.

Example:
    report = deep_research(
        "What are the best practices for Python async programming in 2025?",
        num_searches=3,
        results_per_search=3
    )
"""


# =============================================================================
# Utility Functions
# =============================================================================


def _get_ddgs() -> type:
    """Import and return the DDGS class.

    Returns:
        DDGS class from duckduckgo_search.

    Raises:
        ImportError: If duckduckgo-search is not installed.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError as e:
        msg = (
            "duckduckgo-search is required for web search. "
            "Install it with: pip install duckduckgo-search"
        )
        raise ImportError(msg) from e
    else:
        return DDGS


def _extract_text_from_html(html: str) -> str:
    """Extract main text content from HTML.

    Args:
        html: Raw HTML string.

    Returns:
        Extracted text content.
    """
    try:
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.text_parts: list[str] = []
                self._skip_tags = {"script", "style", "head", "meta", "link", "noscript"}
                self._current_skip = False
                self._skip_depth = 0

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
                if tag.lower() in self._skip_tags:
                    self._current_skip = True
                    self._skip_depth += 1

            def handle_endtag(self, tag: str) -> None:
                if tag.lower() in self._skip_tags and self._skip_depth > 0:
                    self._skip_depth -= 1
                    if self._skip_depth == 0:
                        self._current_skip = False

            def handle_data(self, data: str) -> None:
                if not self._current_skip:
                    text = data.strip()
                    if text:
                        self.text_parts.append(text)

        extractor = TextExtractor()
        extractor.feed(html)
        return "\n".join(extractor.text_parts)
    except Exception:  # noqa: BLE001
        # Fallback: simple regex-based extraction
        import re

        # Remove script and style content
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()


def _truncate_content(content: str, max_chars: int = 8000) -> str:
    """Truncate content to a maximum character limit.

    Args:
        content: The content to truncate.
        max_chars: Maximum number of characters.

    Returns:
        Truncated content with indicator if truncated.
    """
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + "\n\n[Content truncated...]"


# =============================================================================
# Core Search Functions
# =============================================================================


def web_search_sync(
    query: str,
    *,
    max_results: int = 5,
    region: RegionType = "wt-wt",
    timelimit: TimeLimitType = None,
    safesearch: SafeSearchType = "moderate",
) -> list[dict[str, str]]:
    """Perform a synchronous web search using DuckDuckGo.

    Args:
        query: The search query string.
        max_results: Maximum number of results (default: 5, max: 20).
        region: Region code for localized results.
        timelimit: Time filter - "d", "w", "m", "y" or None.
        safesearch: Safe search level.

    Returns:
        List of search results with title, href, and body keys.
    """
    ddgs_class = _get_ddgs()
    max_results = min(max_results, 20)

    try:
        results = ddgs_class().text(
            query,
            region=region,
            safesearch=safesearch,
            timelimit=timelimit,
            max_results=max_results,
        )
        return list(results) if results else []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Web search failed for query '{query}': {e}")
        return [{"error": str(e), "query": query}]


async def web_search_async(
    query: str,
    *,
    max_results: int = 5,
    region: RegionType = "wt-wt",
    timelimit: TimeLimitType = None,
    safesearch: SafeSearchType = "moderate",
) -> list[dict[str, str]]:
    """Perform an asynchronous web search using DuckDuckGo.

    Args:
        query: The search query string.
        max_results: Maximum number of results (default: 5, max: 20).
        region: Region code for localized results.
        timelimit: Time filter - "d", "w", "m", "y" or None.
        safesearch: Safe search level.

    Returns:
        List of search results with title, href, and body keys.
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return await loop.run_in_executor(
            executor,
            lambda: web_search_sync(
                query,
                max_results=max_results,
                region=region,
                timelimit=timelimit,
                safesearch=safesearch,
            ),
        )


def web_fetch_sync(url: str, *, timeout: int = 10) -> dict[str, str]:
    """Fetch and extract content from a URL synchronously.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Dict with url, title, content, and error keys.
    """
    import urllib.request
    from urllib.error import HTTPError, URLError

    result: dict[str, str] = {"url": url, "title": "", "content": "", "error": ""}

    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            result["error"] = "Invalid URL format"
            return result
    except Exception:  # noqa: BLE001
        result["error"] = "Invalid URL"
        return result

    try:
        # Create request with user agent
        request = urllib.request.Request(  # noqa: S310
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower() and "text/plain" not in content_type.lower():
                result["error"] = f"Unsupported content type: {content_type}"
                return result

            html = response.read().decode("utf-8", errors="ignore")

            # Extract title
            import re

            title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            if title_match:
                result["title"] = title_match.group(1).strip()

            # Extract text content
            result["content"] = _truncate_content(_extract_text_from_html(html))

    except HTTPError as e:
        result["error"] = f"HTTP Error {e.code}: {e.reason}"
    except URLError as e:
        result["error"] = f"URL Error: {e.reason}"
    except TimeoutError:
        result["error"] = "Request timed out"
    except Exception as e:  # noqa: BLE001
        result["error"] = f"Error: {e!s}"

    return result


async def web_fetch_async(url: str, *, request_timeout: int = 10) -> dict[str, str]:
    """Fetch and extract content from a URL asynchronously.

    Args:
        url: The URL to fetch.
        request_timeout: Request timeout in seconds.

    Returns:
        Dict with url, title, content, and error keys.
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return await loop.run_in_executor(executor, lambda: web_fetch_sync(url, timeout=request_timeout))


# =============================================================================
# Deep Research Functions
# =============================================================================


def _generate_search_queries(query: str, num_queries: int = 3) -> list[str]:
    """Generate multiple search queries for comprehensive research.

    Args:
        query: The original research query.
        num_queries: Number of queries to generate.

    Returns:
        List of search queries.
    """
    # Basic query variations - could be enhanced with LLM
    queries = [query]

    # Add variations
    variations = [
        f"{query} best practices",
        f"{query} examples",
        f"{query} guide",
        f"{query} tutorial",
        f"how to {query}",
        f"{query} 2025",
    ]

    for var in variations:
        if len(queries) >= num_queries:
            break
        if var != query:
            queries.append(var)

    return queries[:num_queries]


def deep_research_sync(
    query: str,
    *,
    model: BaseChatModel | None = None,
    num_searches: int = 3,
    results_per_search: int = 3,
    include_sources: bool = True,
    region: RegionType = "wt-wt",
) -> str:
    """Perform deep research on a topic synchronously.

    Args:
        query: The research question or topic.
        model: LLM to use for synthesis (optional, returns raw data if not provided).
        num_searches: Number of search queries to generate.
        results_per_search: Results to fetch per search.
        include_sources: Include source URLs in the report.
        region: Region for search results.

    Returns:
        Research report as a string.
    """
    num_searches = min(num_searches, 5)
    results_per_search = min(results_per_search, 5)

    # Generate search queries
    search_queries = _generate_search_queries(query, num_searches)

    # Collect all search results
    all_results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for search_query in search_queries:
        results = web_search_sync(
            search_query,
            max_results=results_per_search,
            region=region,
        )
        for result in results:
            if "error" not in result and result.get("href"):
                url = result["href"]
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(result)

    if not all_results:
        return f"No search results found for: {query}"

    # Fetch content from top results
    fetched_content: list[dict[str, str]] = []
    urls_to_fetch = [r["href"] for r in all_results[:num_searches * results_per_search]]

    for url in urls_to_fetch:
        content = web_fetch_sync(url, timeout=10)
        if not content.get("error") and content.get("content"):
            fetched_content.append(content)

    if not fetched_content:
        # Fall back to search snippets
        snippets = "\n\n".join(
            [f"**{r.get('title', 'No title')}**\n{r.get('body', 'No content')}\nSource: {r.get('href', 'N/A')}" for r in all_results[:5]]
        )
        if model:
            return _synthesize_with_llm(query, snippets, [], model, include_sources=include_sources)
        return f"Research results for: {query}\n\n{snippets}"

    # Prepare content for synthesis
    content_parts = []
    sources = []
    for item in fetched_content:
        content_parts.append(f"## {item.get('title', 'Untitled')}\n\n{item.get('content', '')[:3000]}")
        sources.append(item.get("url", ""))

    combined_content = "\n\n---\n\n".join(content_parts)

    if model:
        return _synthesize_with_llm(query, combined_content, sources, model, include_sources=include_sources)

    # Return raw content if no model provided
    report = f"# Research: {query}\n\n{combined_content}"
    if include_sources and sources:
        report += "\n\n## Sources\n" + "\n".join(f"- {s}" for s in sources if s)
    return report


def _synthesize_with_llm(
    query: str,
    content: str,
    sources: list[str],
    model: BaseChatModel,
    *,
    include_sources: bool,
) -> str:
    """Synthesize research content using an LLM.

    Args:
        query: The original research query.
        content: Combined content from web sources.
        sources: List of source URLs.
        model: LLM to use for synthesis.
        include_sources: Whether to include sources in output.

    Returns:
        Synthesized research report.
    """
    synthesis_prompt = f"""You are a research assistant. Synthesize the following web content \
into a comprehensive, well-organized research report answering the query.

Query: {query}

Web Content:
{content[:15000]}

Instructions:
1. Provide a clear, organized answer to the query
2. Include relevant details, examples, and best practices
3. Cite specific information where appropriate
4. Be objective and comprehensive
5. Use markdown formatting for readability

Write a comprehensive research report:"""

    try:
        response = model.invoke(synthesis_prompt)
        report = response.content if hasattr(response, "content") else str(response)

        if include_sources and sources:
            valid_sources = [s for s in sources if s]
            if valid_sources:
                report += "\n\n## Sources\n" + "\n".join(f"- {s}" for s in valid_sources)

        return str(report)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM synthesis failed: {e}")
        # Fall back to raw content
        report = f"# Research: {query}\n\n{content[:8000]}"
        if include_sources and sources:
            report += "\n\n## Sources\n" + "\n".join(f"- {s}" for s in sources if s)
        return report


async def deep_research_async(
    query: str,
    *,
    model: BaseChatModel | None = None,
    num_searches: int = 3,
    results_per_search: int = 3,
    include_sources: bool = True,
    region: RegionType = "wt-wt",
) -> str:
    """Perform deep research on a topic asynchronously.

    Args:
        query: The research question or topic.
        model: LLM to use for synthesis (optional).
        num_searches: Number of search queries to generate.
        results_per_search: Results to fetch per search.
        include_sources: Include source URLs in the report.
        region: Region for search results.

    Returns:
        Research report as a string.
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return await loop.run_in_executor(
            executor,
            lambda: deep_research_sync(
                query,
                model=model,
                num_searches=num_searches,
                results_per_search=results_per_search,
                include_sources=include_sources,
                region=region,
            ),
        )


# =============================================================================
# Deprecated Tavily Functions
# =============================================================================


def tavily_search(*args: Any, **kwargs: Any) -> list[dict[str, str]]:
    """Deprecated: Use web_search instead.

    This function is deprecated in favor of web_search which uses DuckDuckGo
    and does not require an API key.
    """
    warnings.warn(
        "tavily_search is deprecated. Use web_search instead, which uses DuckDuckGo "
        "and does not require an API key.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Redirect to web_search
    query = args[0] if args else kwargs.get("query", "")
    return web_search_sync(query)


# =============================================================================
# Tool Generators
# =============================================================================


def _web_search_tool_generator(
    region: RegionType = "wt-wt",
    safesearch: SafeSearchType = "moderate",
) -> BaseTool:
    """Generate the web_search tool.

    Args:
        region: Default region for searches.
        safesearch: Default safe search level.

    Returns:
        The web_search tool.
    """

    @tool
    def web_search(
        query: str,
        max_results: int = 5,
        timelimit: str | None = None,
    ) -> list[dict[str, str]]:
        """Search the web using DuckDuckGo (no API key required).

        Args:
            query: The search query string.
            max_results: Maximum number of results (default: 5, max: 20).
            timelimit: Time filter - "d" (day), "w" (week), "m" (month), "y" (year).

        Returns:
            List of search results with title, href (URL), and body (snippet).
        """
        return web_search_sync(
            query,
            max_results=max_results,
            region=region,
            timelimit=timelimit if timelimit in ("d", "w", "m", "y") else None,  # type: ignore[arg-type]
            safesearch=safesearch,
        )

    return web_search


def _web_fetch_tool_generator() -> BaseTool:
    """Generate the web_fetch tool.

    Returns:
        The web_fetch tool.
    """

    @tool
    def web_fetch(url: str, timeout: int = 10) -> dict[str, str]:
        """Fetch and extract content from a URL.

        Args:
            url: The URL to fetch content from.
            timeout: Request timeout in seconds (default: 10).

        Returns:
            Dict with url, title, content, and error (if any).
        """
        return web_fetch_sync(url, timeout=timeout)

    return web_fetch


def _deep_research_tool_generator(
    model: BaseChatModel | None = None,
    region: RegionType = "wt-wt",
) -> BaseTool:
    """Generate the deep_research tool.

    Args:
        model: LLM to use for synthesis.
        region: Default region for searches.

    Returns:
        The deep_research tool.
    """

    @tool
    def deep_research(
        query: str,
        num_searches: int = 3,
        results_per_search: int = 3,
        include_sources: bool = True,  # noqa: FBT001, FBT002
    ) -> str:
        """Perform deep web research on a topic.

        Searches multiple queries, fetches content from relevant pages,
        and synthesizes information into a comprehensive report.

        Args:
            query: The research question or topic.
            num_searches: Number of search queries (default: 3, max: 5).
            results_per_search: Results per search (default: 3, max: 5).
            include_sources: Include source URLs (default: True).

        Returns:
            A comprehensive research report.
        """
        return deep_research_sync(
            query,
            model=model,
            num_searches=num_searches,
            results_per_search=results_per_search,
            include_sources=include_sources,
            region=region,
        )

    return deep_research


# =============================================================================
# Web Middleware
# =============================================================================


class WebMiddleware(AgentMiddleware):
    """Middleware for web search and research capabilities.

    This middleware provides three tools:
    - web_search: Search the web using DuckDuckGo (no API key required)
    - web_fetch: Fetch and extract content from URLs
    - deep_research: Comprehensive research with LLM synthesis

    Args:
        model: Optional LLM for deep_research synthesis. If not provided,
            deep_research returns raw content without synthesis.
        region: Default region for searches (default: "wt-wt" worldwide).
        safesearch: Safe search level (default: "moderate").
        include_deep_research: Whether to include the deep_research tool.
        system_prompt: Optional custom system prompt override.

    Example:
        ```python
        from deepagents import create_deep_agent
        from deepagents.middleware.web import WebMiddleware
        from langchain_anthropic import ChatAnthropic

        # Basic usage (no deep research synthesis)
        agent = create_deep_agent(
            middleware=[WebMiddleware()],
        )

        # With LLM for deep research synthesis
        llm = ChatAnthropic(model="claude-sonnet-4-20250514")
        agent = create_deep_agent(
            middleware=[WebMiddleware(model=llm)],
        )

        # Regional search (Brazil)
        agent = create_deep_agent(
            middleware=[WebMiddleware(region="br-pt")],
        )
        ```
    """

    def __init__(
        self,
        *,
        model: BaseChatModel | None = None,
        region: RegionType = "wt-wt",
        safesearch: SafeSearchType = "moderate",
        include_deep_research: bool = True,
        system_prompt: str | None = None,
    ) -> None:
        """Initialize the web middleware.

        Args:
            model: LLM for deep_research synthesis.
            region: Default region for searches.
            safesearch: Safe search level.
            include_deep_research: Include deep_research tool.
            system_prompt: Custom system prompt override.
        """
        self._model = model
        self._region = region
        self._safesearch = safesearch
        self._include_deep_research = include_deep_research
        self._custom_system_prompt = system_prompt
        self._tools: list[BaseTool] = []

    @property
    def tools(self) -> list[BaseTool]:
        """Get web tools.

        Returns:
            List of web tools.
        """
        if self._tools:
            return self._tools

        self._tools = [
            _web_search_tool_generator(region=self._region, safesearch=self._safesearch),
            _web_fetch_tool_generator(),
        ]

        if self._include_deep_research:
            self._tools.append(
                _deep_research_tool_generator(model=self._model, region=self._region)
            )

        return self._tools

    def get_system_prompt_addition(self) -> str:
        """Get the system prompt addition for web tools.

        Returns:
            System prompt text explaining web tools.
        """
        if self._custom_system_prompt is not None:
            return self._custom_system_prompt

        prompt = WEB_SEARCH_SYSTEM_PROMPT
        if self._include_deep_research:
            prompt += "\n\n" + DEEP_RESEARCH_SYSTEM_PROMPT
        return prompt


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "RegionType",
    "SafeSearchType",
    "TimeLimitType",
    "WebMiddleware",
    "deep_research_async",
    "deep_research_sync",
    "tavily_search",
    "web_fetch_async",
    "web_fetch_sync",
    "web_search_async",
    "web_search_sync",
]
