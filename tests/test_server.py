"""Test cases for Hoogle MCP Server."""

import asyncio
from typing import Any
from unittest.mock import ANY, AsyncMock, patch, Mock

import pytest

from hoogle_mcp_server.server import (
    HOOGLE_COMMAND_TIMEOUT_SECONDS,
    MAX_QUERY_LENGTH,
    handle_call_tool,
    handle_hoogle_info,
    handle_hoogle_search,
    run_hoogle_command,
)


class TestRunHoogleCommand:
    """Test cases for run_hoogle_command function."""

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.get_hoogle_path")
    async def test_hoogle_not_found(self, mock_get_hoogle_path: Any) -> None:
        """Test behavior when hoogle command is not found."""
        mock_get_hoogle_path.side_effect = RuntimeError(
            "Hoogle path not initialized. Server startup may have failed."
        )

        result = await run_hoogle_command(["search", "map"])

        assert not result["success"]
        assert result["error"] is not None
        assert "Hoogle path not initialized" in result["error"]

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec")
    @patch("hoogle_mcp_server.server.get_hoogle_path")
    async def test_successful_hoogle_search(
        self, mock_get_hoogle_path: Any, mock_create_subprocess: Any
    ) -> None:
        """Test successful hoogle search command."""
        mock_get_hoogle_path.return_value = "/usr/bin/hoogle"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b"Data.List map :: (a -> b) -> [a] -> [b]\n",
            b"",
        )
        mock_create_subprocess.return_value = mock_process

        result = await run_hoogle_command(["search", "map"])

        assert result["success"]
        assert "Data.List map" in result["output"]
        assert result["return_code"] == 0
        mock_create_subprocess.assert_called_once_with(
            "/usr/bin/hoogle",
            "search",
            "map",
            stdout=ANY,
            stderr=ANY,
        )

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec")
    @patch("hoogle_mcp_server.server.get_hoogle_path")
    async def test_hoogle_command_failure(
        self, mock_get_hoogle_path: Any, mock_create_subprocess: Any
    ) -> None:
        """Test hoogle command failure."""
        mock_get_hoogle_path.return_value = "/usr/bin/hoogle"

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Invalid query")
        mock_create_subprocess.return_value = mock_process

        result = await run_hoogle_command(["search", "invalid query"])

        assert not result["success"]
        assert result["error"] == "Invalid query"
        assert result["return_code"] == 1

    @pytest.mark.asyncio
    @patch("asyncio.wait_for")
    @patch("asyncio.create_subprocess_exec")
    @patch("hoogle_mcp_server.server.get_hoogle_path")
    async def test_timeout_handling(
        self, mock_get_hoogle_path: Any, mock_create_subprocess: Any, mock_wait_for: Any
    ) -> None:
        """Test timeout handling."""
        mock_get_hoogle_path.return_value = "/usr/bin/hoogle"

        mock_process = AsyncMock()
        mock_process.kill = Mock()  # kill() should be sync
        mock_process.wait = AsyncMock()  # wait() should be async
        mock_create_subprocess.return_value = mock_process

        mock_wait_for.side_effect = asyncio.TimeoutError()

        result = await run_hoogle_command(["search", "map"])

        assert not result["success"]
        assert result["error"] is not None
        assert "timed out" in result["error"]
        assert f"({HOOGLE_COMMAND_TIMEOUT_SECONDS} seconds)" in result["error"]
        mock_process.kill.assert_called_once()


class TestHandleCallTool:
    """Test cases for handle_call_tool function."""

    @pytest.mark.asyncio
    async def test_hoogle_search_missing_query(self) -> None:
        """Test hoogle_search with missing query parameter."""
        result = await handle_call_tool("hoogle_search", {})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Search query not specified" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_hoogle_search_success(self, mock_run_hoogle: Any) -> None:
        """Test successful hoogle_search."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Data.List map :: (a -> b) -> [a] -> [b]\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_call_tool("hoogle_search", {"query": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        mock_run_hoogle.assert_called_once_with(
            ["search", "--count", "10", "--", "map"]
        )

    @pytest.mark.asyncio
    async def test_hoogle_info_missing_name(self) -> None:
        """Test hoogle_info with missing name parameter."""
        result = await handle_call_tool("hoogle_info", {})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Function name or type name not specified" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_hoogle_info_success(self, mock_run_hoogle: Any) -> None:
        """Test successful hoogle_info."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Detailed information about map function\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_call_tool("hoogle_info", {"name": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Detailed information" in result[0].text
        mock_run_hoogle.assert_called_once_with(["search", "-i", "--", "map"])

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
        assert "Error: Search query not specified" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_query_at_max_length(self, mock_run_hoogle: Any) -> None:
        """Test handle_hoogle_search with query at maximum allowed length."""
        max_length_query = "a" * MAX_QUERY_LENGTH
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Some search results\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_search({"query": max_length_query})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error" not in result[0].text
        assert "Some search results" in result[0].text
        mock_run_hoogle.assert_called_once()

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_success(self, mock_run_hoogle: Any) -> None:
        """Test successful handle_hoogle_search."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Data.List map :: (a -> b) -> [a] -> [b]\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_search({"query": "map", "max_results": 5})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        mock_run_hoogle.assert_called_once_with(["search", "--count", "5", "--", "map"])

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_no_results(self, mock_run_hoogle: Any) -> None:
        """Test handle_hoogle_search with no results."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_search({"query": "nonexistent"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "No search results found" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_error(self, mock_run_hoogle: Any) -> None:
        """Test handle_hoogle_search with error."""
        mock_run_hoogle.return_value = {
            "success": False,
            "output": "",
            "error": "Invalid query",
            "return_code": 1,
        }

        result = await handle_hoogle_search({"query": "invalid"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Search error: Invalid query" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_multiple_results(self, mock_run_hoogle: Any) -> None:
        """Test handle_hoogle_search with multiple results."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": (
                "Data.List map :: (a -> b) -> [a] -> [b]\n"
                "Prelude map :: (a -> b) -> [a] -> [b]\n"
                "Data.Functor fmap :: Functor f => (a -> b) -> f a -> f b\n"
                "Control.Monad liftM :: Monad m => (a1 -> r) -> m a1 -> m r\n"
            ),
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_search({"query": "map", "max_results": 4})

        assert len(result) == 1
        assert result[0].type == "text"
        response_text = result[0].text
        assert "Data.List map" in response_text
        assert "Prelude map" in response_text
        assert "Data.Functor fmap" in response_text
        assert "Control.Monad liftM" in response_text
        mock_run_hoogle.assert_called_once_with(["search", "--count", "4", "--", "map"])


class TestHandleHoogleInfo:
    """Test cases for handle_hoogle_info function."""

    @pytest.mark.asyncio
    async def test_missing_name(self) -> None:
        """Test handle_hoogle_info with missing name parameter."""
        result = await handle_hoogle_info({})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Function name or type name not specified" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_name_at_max_length(self, mock_run_hoogle: Any) -> None:
        """Test handle_hoogle_info with name at maximum allowed length."""
        max_length_name = "a" * MAX_QUERY_LENGTH
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Some function info\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_info({"name": max_length_name})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error" not in result[0].text
        assert "Some function info" in result[0].text
        mock_run_hoogle.assert_called_once()

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_success(self, mock_run_hoogle: Any) -> None:
        """Test successful handle_hoogle_info."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Detailed information about map function\n",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_info({"name": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Detailed information" in result[0].text
        mock_run_hoogle.assert_called_once_with(["search", "-i", "--", "map"])

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_no_info(self, mock_run_hoogle: Any) -> None:
        """Test handle_hoogle_info with no information found."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "",
            "error": None,
            "return_code": 0,
        }

        result = await handle_hoogle_info({"name": "nonexistent"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "No information found" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_error(self, mock_run_hoogle: Any) -> None:
        """Test handle_hoogle_info with error."""
        mock_run_hoogle.return_value = {
            "success": False,
            "output": "",
            "error": "Function not found",
            "return_code": 1,
        }

        result = await handle_hoogle_info({"name": "invalid"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Information retrieval error: Function not found" in result[0].text
