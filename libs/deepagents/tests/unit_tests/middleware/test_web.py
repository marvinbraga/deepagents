"""Unit tests for WebMiddleware."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from deepagents.middleware.web import (
    WebMiddleware,
    _extract_text_from_html,
    _generate_search_queries,
    _truncate_content,
    tavily_search,
    web_fetch_sync,
    web_search_sync,
)

if TYPE_CHECKING:
    pass


class TestWebMiddleware:
    """Tests for WebMiddleware class."""

    def test_middleware_provides_default_tools(self):
        """Middleware should provide web_search, web_fetch, and deep_research by default."""
        middleware = WebMiddleware()
        tools = middleware.tools

        tool_names = [t.name for t in tools]
        assert "web_search" in tool_names
        assert "web_fetch" in tool_names
        assert "deep_research" in tool_names
        assert len(tools) == 3

    def test_middleware_without_deep_research(self):
        """Middleware should work without deep_research tool."""
        middleware = WebMiddleware(include_deep_research=False)
        tools = middleware.tools

        tool_names = [t.name for t in tools]
        assert "web_search" in tool_names
        assert "web_fetch" in tool_names
        assert "deep_research" not in tool_names
        assert len(tools) == 2

    def test_tools_property_cached(self):
        """Tools should be cached after first access."""
        middleware = WebMiddleware()

        tools1 = middleware.tools
        tools2 = middleware.tools

        # Should be the exact same list object
        assert tools1 is tools2

    def test_system_prompt_addition(self):
        """Middleware should provide system prompt addition."""
        middleware = WebMiddleware()
        prompt = middleware.get_system_prompt_addition()

        assert len(prompt) > 0
        assert "web_search" in prompt
        assert "web_fetch" in prompt

    def test_system_prompt_with_deep_research(self):
        """System prompt should include deep research when enabled."""
        middleware = WebMiddleware(include_deep_research=True)
        prompt = middleware.get_system_prompt_addition()

        assert "deep_research" in prompt

    def test_system_prompt_without_deep_research(self):
        """System prompt should not mention deep research when disabled."""
        middleware = WebMiddleware(include_deep_research=False)
        prompt = middleware.get_system_prompt_addition()

        assert "Deep Research" not in prompt

    def test_custom_system_prompt(self):
        """Custom system prompt should override default."""
        custom = "Custom web prompt"
        middleware = WebMiddleware(system_prompt=custom)
        prompt = middleware.get_system_prompt_addition()

        assert prompt == custom

    def test_region_configuration(self):
        """Region should be configurable."""
        middleware = WebMiddleware(region="br-pt")
        assert middleware._region == "br-pt"

    def test_safesearch_configuration(self):
        """Safe search should be configurable."""
        middleware = WebMiddleware(safesearch="off")
        assert middleware._safesearch == "off"


class TestWebSearchTool:
    """Tests for web_search tool."""

    @pytest.fixture
    def search_tool(self):
        """Get the web_search tool."""
        middleware = WebMiddleware()
        tools = middleware.tools
        return next(t for t in tools if t.name == "web_search")

    def test_tool_has_correct_name(self, search_tool):
        """Tool should have correct name."""
        assert search_tool.name == "web_search"

    def test_tool_has_description(self, search_tool):
        """Tool should have a description."""
        assert search_tool.description is not None
        assert len(search_tool.description) > 0
        assert "DuckDuckGo" in search_tool.description


class TestWebFetchTool:
    """Tests for web_fetch tool."""

    @pytest.fixture
    def fetch_tool(self):
        """Get the web_fetch tool."""
        middleware = WebMiddleware()
        tools = middleware.tools
        return next(t for t in tools if t.name == "web_fetch")

    def test_tool_has_correct_name(self, fetch_tool):
        """Tool should have correct name."""
        assert fetch_tool.name == "web_fetch"

    def test_tool_has_description(self, fetch_tool):
        """Tool should have a description."""
        assert fetch_tool.description is not None
        assert len(fetch_tool.description) > 0


class TestDeepResearchTool:
    """Tests for deep_research tool."""

    @pytest.fixture
    def research_tool(self):
        """Get the deep_research tool."""
        middleware = WebMiddleware()
        tools = middleware.tools
        return next(t for t in tools if t.name == "deep_research")

    def test_tool_has_correct_name(self, research_tool):
        """Tool should have correct name."""
        assert research_tool.name == "deep_research"

    def test_tool_has_description(self, research_tool):
        """Tool should have a description."""
        assert research_tool.description is not None
        assert len(research_tool.description) > 0
        assert "research" in research_tool.description.lower()


class TestWebSearchSync:
    """Tests for web_search_sync function."""

    def test_search_with_missing_ddgs(self):
        """Should raise ImportError when duckduckgo-search is not installed."""
        with patch.dict("sys.modules", {"duckduckgo_search": None}):
            with patch("deepagents.middleware.web._get_ddgs") as mock_get:
                mock_get.side_effect = ImportError("duckduckgo-search is required")

                with pytest.raises(ImportError, match="duckduckgo-search"):
                    web_search_sync("test query")

    def test_search_returns_list(self):
        """Search should return a list of results."""
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet 1"},
            {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet 2"},
        ]

        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        with patch("deepagents.middleware.web._get_ddgs", return_value=mock_ddgs_class):
            results = web_search_sync("test query", max_results=2)

        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["title"] == "Result 1"

    def test_search_respects_max_results_limit(self):
        """Max results should be capped at 20."""
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = []

        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        with patch("deepagents.middleware.web._get_ddgs", return_value=mock_ddgs_class):
            web_search_sync("test query", max_results=100)

        # Verify it was called with max 20
        call_kwargs = mock_ddgs_instance.text.call_args.kwargs
        assert call_kwargs["max_results"] == 20

    def test_search_handles_exception(self):
        """Search should handle exceptions gracefully."""
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.side_effect = Exception("Network error")

        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        with patch("deepagents.middleware.web._get_ddgs", return_value=mock_ddgs_class):
            results = web_search_sync("test query")

        assert isinstance(results, list)
        assert len(results) == 1
        assert "error" in results[0]

    def test_search_with_region(self):
        """Search should pass region parameter."""
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = []

        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        with patch("deepagents.middleware.web._get_ddgs", return_value=mock_ddgs_class):
            web_search_sync("test query", region="br-pt")

        call_kwargs = mock_ddgs_instance.text.call_args.kwargs
        assert call_kwargs["region"] == "br-pt"

    def test_search_with_timelimit(self):
        """Search should pass timelimit parameter."""
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = []

        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        with patch("deepagents.middleware.web._get_ddgs", return_value=mock_ddgs_class):
            web_search_sync("test query", timelimit="w")

        call_kwargs = mock_ddgs_instance.text.call_args.kwargs
        assert call_kwargs["timelimit"] == "w"


class TestWebFetchSync:
    """Tests for web_fetch_sync function."""

    def test_fetch_invalid_url(self):
        """Fetch should handle invalid URLs."""
        result = web_fetch_sync("not-a-valid-url")

        assert "error" in result
        assert result["error"] != ""

    def test_fetch_empty_url(self):
        """Fetch should handle empty URL."""
        result = web_fetch_sync("")

        assert "error" in result
        assert "Invalid URL" in result["error"]

    def test_fetch_returns_dict_structure(self):
        """Fetch should return dict with expected keys."""
        result = web_fetch_sync("invalid://test")

        assert "url" in result
        assert "title" in result
        assert "content" in result
        assert "error" in result

    def test_fetch_successful(self):
        """Fetch should extract content from HTML."""
        html_content = b"""
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is test content.</p>
        </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.read.return_value = html_content
        mock_response.headers.get.return_value = "text/html"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = web_fetch_sync("https://example.com")

        assert result["title"] == "Test Page"
        assert "Hello World" in result["content"]
        assert "test content" in result["content"]
        assert result["error"] == ""

    def test_fetch_handles_timeout(self):
        """Fetch should handle timeout errors."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError()):
            result = web_fetch_sync("https://example.com")

        assert "timed out" in result["error"].lower() or "timeout" in result["error"].lower()


class TestExtractTextFromHtml:
    """Tests for _extract_text_from_html function."""

    def test_extracts_basic_text(self):
        """Should extract text from simple HTML."""
        html = "<html><body><p>Hello World</p></body></html>"
        result = _extract_text_from_html(html)

        assert "Hello World" in result

    def test_removes_script_tags(self):
        """Should remove script content."""
        html = "<html><body><script>alert('evil')</script><p>Safe content</p></body></html>"
        result = _extract_text_from_html(html)

        assert "alert" not in result
        assert "evil" not in result
        assert "Safe content" in result

    def test_removes_style_tags(self):
        """Should remove style content."""
        html = "<html><head><style>body { color: red; }</style></head><body><p>Content</p></body></html>"
        result = _extract_text_from_html(html)

        assert "color" not in result
        assert "Content" in result

    def test_handles_empty_html(self):
        """Should handle empty HTML."""
        result = _extract_text_from_html("")
        assert result == ""

    def test_handles_nested_tags(self):
        """Should extract text from nested tags."""
        html = "<div><div><span>Nested</span> text</div></div>"
        result = _extract_text_from_html(html)

        assert "Nested" in result
        assert "text" in result


class TestTruncateContent:
    """Tests for _truncate_content function."""

    def test_no_truncation_under_limit(self):
        """Content under limit should not be truncated."""
        content = "Short content"
        result = _truncate_content(content, max_chars=100)

        assert result == content
        assert "[truncated]" not in result

    def test_truncation_over_limit(self):
        """Content over limit should be truncated."""
        content = "A" * 200
        result = _truncate_content(content, max_chars=100)

        assert len(result) < len(content)
        assert "[Content truncated...]" in result

    def test_truncation_exact_limit(self):
        """Content exactly at limit should not be truncated."""
        content = "A" * 100
        result = _truncate_content(content, max_chars=100)

        assert result == content


class TestGenerateSearchQueries:
    """Tests for _generate_search_queries function."""

    def test_returns_original_query(self):
        """Should always include the original query."""
        queries = _generate_search_queries("test topic", num_queries=3)

        assert queries[0] == "test topic"

    def test_respects_num_queries(self):
        """Should return requested number of queries."""
        queries = _generate_search_queries("test topic", num_queries=3)

        assert len(queries) == 3

    def test_single_query(self):
        """Should work with single query request."""
        queries = _generate_search_queries("test topic", num_queries=1)

        assert len(queries) == 1
        assert queries[0] == "test topic"

    def test_generates_variations(self):
        """Should generate query variations."""
        queries = _generate_search_queries("python", num_queries=3)

        # All queries should be different
        assert len(set(queries)) == len(queries)


class TestTavilySearchDeprecated:
    """Tests for deprecated tavily_search function."""

    def test_raises_deprecation_warning(self):
        """tavily_search should raise DeprecationWarning."""
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = []
        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        with patch("deepagents.middleware.web._get_ddgs", return_value=mock_ddgs_class):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                tavily_search("test query")

                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "deprecated" in str(w[0].message).lower()
                assert "web_search" in str(w[0].message)

    def test_redirects_to_web_search(self):
        """tavily_search should redirect to web_search."""
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [{"title": "Test", "href": "http://test.com", "body": "Test"}]
        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        with patch("deepagents.middleware.web._get_ddgs", return_value=mock_ddgs_class):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = tavily_search("test query")

        assert isinstance(result, list)


class TestMultipleMiddlewareInstances:
    """Tests for multiple middleware instance independence."""

    def test_instances_independent(self):
        """Multiple middleware instances should be independent."""
        middleware1 = WebMiddleware(region="us-en")
        middleware2 = WebMiddleware(region="br-pt")

        assert middleware1._region == "us-en"
        assert middleware2._region == "br-pt"

        # Tools should be different instances
        tools1 = middleware1.tools
        tools2 = middleware2.tools

        assert tools1 is not tools2

    def test_model_configuration(self):
        """Middleware should accept model configuration."""
        mock_model = MagicMock()
        middleware = WebMiddleware(model=mock_model)

        assert middleware._model is mock_model
