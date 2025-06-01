"""Test cases for Hoogle MCP Server."""

from typing import Generator
from unittest.mock import Mock

import pytest

from hoogle_mcp_server.hoogle_client import HoogleClient
from hoogle_mcp_server.server import (
    MAX_QUERY_LENGTH,
    handle_call_tool,
    handle_hoogle_info,
    handle_hoogle_search,
)
import hoogle_mcp_server.server as server_module


@pytest.fixture
def setup_hoogle_client() -> Generator[Mock, None, None]:
    """Set up a mock hoogle client for testing."""
    mock_client = Mock(spec=HoogleClient)
    server_module.hoogle_client = mock_client
    yield mock_client
    server_module.hoogle_client = None


class TestHoogleClientIntegration:
    """Test cases for HoogleClient integration."""

    @pytest.mark.asyncio
    async def test_search_success(self, setup_hoogle_client: Mock) -> None:
        """Test successful hoogle search through client."""
        setup_hoogle_client.search.return_value = {
            "success": True,
            "output": "Data.List map :: (a -> b) -> [a] -> [b]\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_search({"query": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        setup_hoogle_client.search.assert_called_once_with("map", 10)

    @pytest.mark.asyncio
    async def test_info_success(self, setup_hoogle_client: Mock) -> None:
        """Test successful hoogle info through client."""
        setup_hoogle_client.get_info.return_value = {
            "success": True,
            "output": "Detailed information about map function\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_info({"name": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Detailed information" in result[0].text
        setup_hoogle_client.get_info.assert_called_once_with("map")


class TestHandleCallTool:
    """Test cases for handle_call_tool function."""

    @pytest.mark.asyncio
    async def test_hoogle_search_missing_query(self) -> None:
        """Test hoogle_search with missing query parameter."""
        result = await handle_call_tool("hoogle_search", {})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Hoogle client not initialized" in result[0].text

    @pytest.mark.asyncio
    async def test_hoogle_search_success(self, setup_hoogle_client: Mock) -> None:
        """Test successful hoogle_search."""
        setup_hoogle_client.search.return_value = {
            "success": True,
            "output": "Data.List map :: (a -> b) -> [a] -> [b]\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_call_tool("hoogle_search", {"query": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        setup_hoogle_client.search.assert_called_once_with("map", 10)

    @pytest.mark.asyncio
    async def test_hoogle_info_missing_name(self) -> None:
        """Test hoogle_info with missing name parameter."""
        result = await handle_call_tool("hoogle_info", {})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Hoogle client not initialized" in result[0].text

    @pytest.mark.asyncio
    async def test_hoogle_info_success(self, setup_hoogle_client: Mock) -> None:
        """Test successful hoogle_info."""
        setup_hoogle_client.get_info.return_value = {
            "success": True,
            "output": "Detailed information about map function\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_call_tool("hoogle_info", {"name": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Detailed information" in result[0].text
        setup_hoogle_client.get_info.assert_called_once_with("map")

    @pytest.mark.asyncio
    async def test_unknown_tool(self) -> None:
        """Test call to unknown tool."""
        result = await handle_call_tool("unknown_tool", {})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Unknown tool" in result[0].text


class TestHandleHoogleSearch:
    """Test cases for handle_hoogle_search function."""

    @pytest.mark.asyncio
    async def test_missing_query(self) -> None:
        """Test handle_hoogle_search with missing query parameter."""
        result = await handle_hoogle_search({})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Hoogle client not initialized" in result[0].text

    @pytest.mark.asyncio
    async def test_query_at_max_length(self, setup_hoogle_client: Mock) -> None:
        """Test handle_hoogle_search with query at maximum allowed length."""
        max_length_query = "a" * MAX_QUERY_LENGTH
        setup_hoogle_client.search.return_value = {
            "success": True,
            "output": "Some search results\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_search({"query": max_length_query})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Some search results" in result[0].text
        setup_hoogle_client.search.assert_called_once_with(max_length_query, 10)

    @pytest.mark.asyncio
    async def test_success(self, setup_hoogle_client: Mock) -> None:
        """Test successful search."""
        setup_hoogle_client.search.return_value = {
            "success": True,
            "output": "Data.List map :: (a -> b) -> [a] -> [b]\nPrelude filter :: (a -> Bool) -> [a] -> [a]\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_search({"query": "map", "max_results": 5})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        assert "Prelude filter" in result[0].text
        setup_hoogle_client.search.assert_called_once_with("map", 5)

    @pytest.mark.asyncio
    async def test_no_results(self, setup_hoogle_client: Mock) -> None:
        """Test search with no results."""
        setup_hoogle_client.search.return_value = {
            "success": True,
            "output": "",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_search({"query": "nonexistent_function"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "No search results found" in result[0].text
        setup_hoogle_client.search.assert_called_once_with("nonexistent_function", 10)

    @pytest.mark.asyncio
    async def test_error(self, setup_hoogle_client: Mock) -> None:
        """Test search with error."""
        setup_hoogle_client.search.return_value = {
            "success": False,
            "output": "",
            "error": "Invalid query format",
            "return_code": 1,
        }

        result = await handle_hoogle_search({"query": "invalid query"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Search error" in result[0].text
        assert "Invalid query format" in result[0].text
        setup_hoogle_client.search.assert_called_once_with("invalid query", 10)

    @pytest.mark.asyncio
    async def test_multiple_results(self, setup_hoogle_client: Mock) -> None:
        """Test search with multiple results."""
        setup_hoogle_client.search.return_value = {
            "success": True,
            "output": (
                "Data.List map :: (a -> b) -> [a] -> [b]\n"
                "Prelude map :: (a -> b) -> [a] -> [b]\n"
                "Control.Monad mapM :: Monad m => (a -> m b) -> [a] -> m [b]\n"
            ),
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_search({"query": "map", "max_results": 20})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        assert "Control.Monad mapM" in result[0].text
        setup_hoogle_client.search.assert_called_once_with("map", 20)


class TestHandleHoogleInfo:
    """Test cases for handle_hoogle_info function."""

    @pytest.mark.asyncio
    async def test_missing_name(self) -> None:
        """Test handle_hoogle_info with missing name parameter."""
        result = await handle_hoogle_info({})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Hoogle client not initialized" in result[0].text

    @pytest.mark.asyncio
    async def test_name_at_max_length(self, setup_hoogle_client: Mock) -> None:
        """Test handle_hoogle_info with name at maximum allowed length."""
        max_length_name = "a" * MAX_QUERY_LENGTH
        setup_hoogle_client.get_info.return_value = {
            "success": True,
            "output": "Some detailed information\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_info({"name": max_length_name})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Some detailed information" in result[0].text
        setup_hoogle_client.get_info.assert_called_once_with(max_length_name)

    @pytest.mark.asyncio
    async def test_success(self, setup_hoogle_client: Mock) -> None:
        """Test successful info retrieval."""
        setup_hoogle_client.get_info.return_value = {
            "success": True,
            "output": "module Prelude\nmap :: (a -> b) -> [a] -> [b]\nDetailed docs...\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_info({"name": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "module Prelude" in result[0].text
        assert "Detailed docs" in result[0].text
        setup_hoogle_client.get_info.assert_called_once_with("map")

    @pytest.mark.asyncio
    async def test_no_info(self, setup_hoogle_client: Mock) -> None:
        """Test info retrieval with no information found."""
        setup_hoogle_client.get_info.return_value = {
            "success": True,
            "output": "",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_info({"name": "nonexistent_function"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "No information found" in result[0].text
        setup_hoogle_client.get_info.assert_called_once_with("nonexistent_function")

    @pytest.mark.asyncio
    async def test_error(self, setup_hoogle_client: Mock) -> None:
        """Test info retrieval with error."""
        setup_hoogle_client.get_info.return_value = {
            "success": False,
            "output": "",
            "error": "Function not found",
            "return_code": 1,
        }

        result = await handle_hoogle_info({"name": "invalid_function"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Information retrieval error" in result[0].text
        assert "Function not found" in result[0].text
        setup_hoogle_client.get_info.assert_called_once_with("invalid_function")
