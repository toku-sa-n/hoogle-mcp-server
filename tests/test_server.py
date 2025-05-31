"""Test cases for Hoogle MCP Server."""

from unittest.mock import MagicMock, patch

import pytest

from hoogle_mcp_server.server import (
    HOOGLE_COMMAND_TIMEOUT_SECONDS,
    handle_call_tool,
    handle_hoogle_info,
    handle_hoogle_search,
    run_hoogle_command,
)


class TestRunHoogleCommand:
    """Test cases for run_hoogle_command function."""

    @patch("shutil.which")
    def test_hoogle_not_found(self, mock_which):
        """Test behavior when hoogle command is not found."""
        mock_which.return_value = None

        result = run_hoogle_command(["search", "map"])

        assert not result["success"]
        assert "hoogle command not found" in result["error"]
        assert "Please check your Haskell platform installation" in result["error"]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_successful_hoogle_search(self, mock_which, mock_run):
        """Test successful hoogle search command."""
        mock_which.return_value = "/usr/bin/hoogle"
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Data.List map :: (a -> b) -> [a] -> [b]\n", stderr=""
        )

        result = run_hoogle_command(["search", "map"])

        assert result["success"]
        assert "Data.List map" in result["output"]
        assert result["return_code"] == 0
        mock_run.assert_called_once_with(
            ["/usr/bin/hoogle", "search", "map"],
            capture_output=True,
            text=True,
            timeout=HOOGLE_COMMAND_TIMEOUT_SECONDS,
            shell=False,
        )

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_hoogle_command_failure(self, mock_which, mock_run):
        """Test hoogle command failure."""
        mock_which.return_value = "/usr/bin/hoogle"
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Invalid query"
        )

        result = run_hoogle_command(["search", "invalid query"])

        assert not result["success"]
        assert result["error"] == "Invalid query"
        assert result["return_code"] == 1

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_timeout_handling(self, mock_which, mock_run):
        """Test timeout handling."""
        from subprocess import TimeoutExpired

        mock_which.return_value = "/usr/bin/hoogle"
        mock_run.side_effect = TimeoutExpired("hoogle", HOOGLE_COMMAND_TIMEOUT_SECONDS)

        result = run_hoogle_command(["search", "map"])

        assert not result["success"]
        assert "timed out" in result["error"]
        assert f"({HOOGLE_COMMAND_TIMEOUT_SECONDS} seconds)" in result["error"]


class TestHandleCallTool:
    """Test cases for handle_call_tool function."""

    @pytest.mark.asyncio
    async def test_hoogle_search_missing_query(self):
        """Test hoogle_search with missing query parameter."""
        result = await handle_call_tool("hoogle_search", {})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Search query not specified" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_hoogle_search_success(self, mock_run_hoogle):
        """Test successful hoogle_search."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Data.List map :: (a -> b) -> [a] -> [b]\n",
            "error": None,
        }

        result = await handle_call_tool("hoogle_search", {"query": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        mock_run_hoogle.assert_called_once_with(
            ["search", "--count", "10", "--", "map"]
        )

    @pytest.mark.asyncio
    async def test_hoogle_info_missing_name(self):
        """Test hoogle_info with missing name parameter."""
        result = await handle_call_tool("hoogle_info", {})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Function name or type name not specified" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_hoogle_info_success(self, mock_run_hoogle):
        """Test successful hoogle_info."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Detailed information about map function\n",
            "error": None,
        }

        result = await handle_call_tool("hoogle_info", {"name": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Detailed information" in result[0].text
        mock_run_hoogle.assert_called_once_with(["search", "-i", "--", "map"])

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test call to unknown tool."""
        result = await handle_call_tool("unknown_tool", {})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Unknown tool" in result[0].text


class TestHandleHoogleSearch:
    """Test cases for handle_hoogle_search function."""

    @pytest.mark.asyncio
    async def test_missing_query(self):
        """Test handle_hoogle_search with missing query parameter."""
        result = await handle_hoogle_search({})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Search query not specified" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_success(self, mock_run_hoogle):
        """Test successful handle_hoogle_search."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Data.List map :: (a -> b) -> [a] -> [b]\n",
            "error": None,
        }

        result = await handle_hoogle_search({"query": "map", "max_results": 5})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        mock_run_hoogle.assert_called_once_with(["search", "--count", "5", "--", "map"])

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_no_results(self, mock_run_hoogle):
        """Test handle_hoogle_search with no results."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "",
            "error": None,
        }

        result = await handle_hoogle_search({"query": "nonexistent"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "No search results found" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_error(self, mock_run_hoogle):
        """Test handle_hoogle_search with error."""
        mock_run_hoogle.return_value = {
            "success": False,
            "output": "",
            "error": "Invalid query",
        }

        result = await handle_hoogle_search({"query": "invalid"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Search error: Invalid query" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_multiple_results(self, mock_run_hoogle):
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
    async def test_missing_name(self):
        """Test handle_hoogle_info with missing name parameter."""
        result = await handle_hoogle_info({})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Function name or type name not specified" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_success(self, mock_run_hoogle):
        """Test successful handle_hoogle_info."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "Detailed information about map function\n",
            "error": None,
        }

        result = await handle_hoogle_info({"name": "map"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Detailed information" in result[0].text
        mock_run_hoogle.assert_called_once_with(["search", "-i", "--", "map"])

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_no_info(self, mock_run_hoogle):
        """Test handle_hoogle_info with no information found."""
        mock_run_hoogle.return_value = {
            "success": True,
            "output": "",
            "error": None,
        }

        result = await handle_hoogle_info({"name": "nonexistent"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "No information found" in result[0].text

    @pytest.mark.asyncio
    @patch("hoogle_mcp_server.server.run_hoogle_command")
    async def test_error(self, mock_run_hoogle):
        """Test handle_hoogle_info with error."""
        mock_run_hoogle.return_value = {
            "success": False,
            "output": "",
            "error": "Function not found",
        }

        result = await handle_hoogle_info({"name": "invalid"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Information retrieval error: Function not found" in result[0].text
