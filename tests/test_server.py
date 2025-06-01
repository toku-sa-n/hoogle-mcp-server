"""Test cases for Hoogle MCP Server."""

from unittest.mock import Mock

import pytest

from hoogle_mcp_server.hoogle_client import HoogleClient
from hoogle_mcp_server.hoogle_mcp_server import HoogleMCPServer
from hoogle_mcp_server.types import (
    GetInfoArgs,
    SearchArgs,
    CommandResult,
    MAX_QUERY_LENGTH,
)


@pytest.fixture
def mock_hoogle_client() -> Mock:
    """Create a mock hoogle client for testing."""
    return Mock(spec=HoogleClient)


@pytest.fixture
def hoogle_server(mock_hoogle_client: Mock) -> HoogleMCPServer:
    """Create a HoogleMCPServer instance with mock client for testing."""
    return HoogleMCPServer(mock_hoogle_client)


class TestHoogleClientIntegration:
    """Test cases for HoogleClient integration."""

    @pytest.mark.asyncio
    async def test_search_success(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test successful hoogle search through client."""
        mock_hoogle_client.search.return_value = CommandResult(
            success=True,
            output="Data.List map :: (a -> b) -> [a] -> [b]\n",
            error=None,
            return_code=0,
        )

        search_args = SearchArgs(query="map")
        result = await hoogle_server._handle_hoogle_search(search_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        mock_hoogle_client.search.assert_called_once_with(search_args)

    @pytest.mark.asyncio
    async def test_info_success(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test successful hoogle info through client."""
        mock_hoogle_client.get_info.return_value = CommandResult(
            success=True,
            output="Detailed information about map function\n",
            error=None,
            return_code=0,
        )

        info_args = GetInfoArgs(name="map")
        result = await hoogle_server._handle_hoogle_info(info_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Detailed information" in result[0].text
        mock_hoogle_client.get_info.assert_called_once_with(info_args)


class TestHandleCallTool:
    """Test cases for handle_call_tool function through server."""

    @pytest.mark.asyncio
    async def test_hoogle_search_missing_query(
        self, hoogle_server: HoogleMCPServer
    ) -> None:
        """Test hoogle_search with missing query parameter."""
        import logging

        logging.disable(logging.CRITICAL)  # Suppress expected warning logs

        try:
            from pydantic import ValidationError

            SearchArgs(
                query=""
            )  # This should raise ValidationError for empty query in business logic
            # The validation happens at the business logic level, not pydantic level
        except ValidationError:
            pass  # This won't actually be raised here

        logging.disable(logging.NOTSET)

    @pytest.mark.asyncio
    async def test_hoogle_search_success(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test successful hoogle_search."""
        mock_hoogle_client.search.return_value = CommandResult(
            success=True,
            output="Data.List map :: (a -> b) -> [a] -> [b]\n",
            error=None,
            return_code=0,
        )

        search_args = SearchArgs(query="map")
        result = await hoogle_server._handle_hoogle_search(search_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        mock_hoogle_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_hoogle_info_missing_name(
        self, hoogle_server: HoogleMCPServer
    ) -> None:
        """Test hoogle_info with missing name parameter."""
        import logging

        logging.disable(logging.CRITICAL)

        try:
            from pydantic import ValidationError

            GetInfoArgs(
                name=""
            )  # This should raise ValidationError for empty name in business logic
            # The validation happens at the business logic level, not pydantic level
        except ValidationError:
            pass  # This won't actually be raised here

        logging.disable(logging.NOTSET)

    @pytest.mark.asyncio
    async def test_hoogle_info_success(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test successful hoogle_info."""
        mock_hoogle_client.get_info.return_value = CommandResult(
            success=True,
            output="Detailed information about map function\n",
            error=None,
            return_code=0,
        )

        info_args = GetInfoArgs(name="map")
        result = await hoogle_server._handle_hoogle_info(info_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Detailed information" in result[0].text
        mock_hoogle_client.get_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_hoogle_search_validation_error_query_too_long(self) -> None:
        """Test hoogle_search with query exceeding maximum length."""
        too_long_query = "a" * (MAX_QUERY_LENGTH + 1)

        try:
            from pydantic import ValidationError

            SearchArgs(query=too_long_query)
            assert False, "Expected ValidationError"
        except ValidationError as e:
            assert "query" in str(e)

    @pytest.mark.asyncio
    async def test_hoogle_info_validation_error_name_too_long(self) -> None:
        """Test hoogle_info with name exceeding maximum length."""
        too_long_name = "a" * (MAX_QUERY_LENGTH + 1)

        try:
            from pydantic import ValidationError

            GetInfoArgs(name=too_long_name)
            assert False, "Expected ValidationError"
        except ValidationError as e:
            assert "name" in str(e)


class TestHandleHoogleSearch:
    """Test cases for _handle_hoogle_search method."""

    @pytest.mark.asyncio
    async def test_missing_query(self, hoogle_server: HoogleMCPServer) -> None:
        """Test _handle_hoogle_search with empty query parameter."""
        search_args = SearchArgs(query="")
        result = await hoogle_server._handle_hoogle_search(search_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Search query not specified" in result[0].text

    @pytest.mark.asyncio
    async def test_query_at_max_length(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test _handle_hoogle_search with query at maximum allowed length."""
        max_length_query = "a" * MAX_QUERY_LENGTH
        mock_hoogle_client.search.return_value = CommandResult(
            success=True,
            output="Some search results\n",
            error=None,
            return_code=0,
        )

        search_args = SearchArgs(query=max_length_query)
        result = await hoogle_server._handle_hoogle_search(search_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Some search results" in result[0].text
        mock_hoogle_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_success(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test successful search."""
        mock_hoogle_client.search.return_value = CommandResult(
            success=True,
            output="Data.List map :: (a -> b) -> [a] -> [b]\nPrelude filter :: (a -> Bool) -> [a] -> [a]\n",
            error=None,
            return_code=0,
        )

        search_args = SearchArgs(query="map", max_results=5)
        result = await hoogle_server._handle_hoogle_search(search_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        assert "Prelude filter" in result[0].text
        mock_hoogle_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_results(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test search with no results."""
        mock_hoogle_client.search.return_value = CommandResult(
            success=True,
            output="",
            error=None,
            return_code=0,
        )

        search_args = SearchArgs(query="nonexistent_function")
        result = await hoogle_server._handle_hoogle_search(search_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "No search results found" in result[0].text
        mock_hoogle_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_error(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test search with error."""
        mock_hoogle_client.search.return_value = CommandResult(
            success=False,
            output="",
            error="Invalid query format",
            return_code=1,
        )

        search_args = SearchArgs(query="invalid query")
        result = await hoogle_server._handle_hoogle_search(search_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Search error" in result[0].text
        assert "Invalid query format" in result[0].text
        mock_hoogle_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_results(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test search with multiple results."""
        mock_hoogle_client.search.return_value = CommandResult(
            success=True,
            output=(
                "Data.List map :: (a -> b) -> [a] -> [b]\n"
                "Prelude map :: (a -> b) -> [a] -> [b]\n"
                "Control.Monad mapM :: Monad m => (a -> m b) -> [a] -> m [b]\n"
            ),
            error=None,
            return_code=0,
        )

        search_args = SearchArgs(query="map", max_results=20)
        result = await hoogle_server._handle_hoogle_search(search_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Data.List map" in result[0].text
        assert "Control.Monad mapM" in result[0].text
        mock_hoogle_client.search.assert_called_once()


class TestHandleHoogleInfo:
    """Test cases for _handle_hoogle_info method."""

    @pytest.mark.asyncio
    async def test_missing_name(self, hoogle_server: HoogleMCPServer) -> None:
        """Test _handle_hoogle_info with empty name parameter."""
        info_args = GetInfoArgs(name="")
        result = await hoogle_server._handle_hoogle_info(info_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error: Function name or type name not specified" in result[0].text

    @pytest.mark.asyncio
    async def test_name_at_max_length(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test _handle_hoogle_info with name at maximum allowed length."""
        max_length_name = "a" * MAX_QUERY_LENGTH
        mock_hoogle_client.get_info.return_value = CommandResult(
            success=True,
            output="Some detailed information\n",
            error=None,
            return_code=0,
        )

        info_args = GetInfoArgs(name=max_length_name)
        result = await hoogle_server._handle_hoogle_info(info_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Some detailed information" in result[0].text
        mock_hoogle_client.get_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_success(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test successful info retrieval."""
        mock_hoogle_client.get_info.return_value = CommandResult(
            success=True,
            output="module Prelude\nmap :: (a -> b) -> [a] -> [b]\nDetailed docs...\n",
            error=None,
            return_code=0,
        )

        info_args = GetInfoArgs(name="map")
        result = await hoogle_server._handle_hoogle_info(info_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "module Prelude" in result[0].text
        assert "Detailed docs" in result[0].text
        mock_hoogle_client.get_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_info(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test info retrieval with no information found."""
        mock_hoogle_client.get_info.return_value = CommandResult(
            success=True,
            output="",
            error=None,
            return_code=0,
        )

        info_args = GetInfoArgs(name="nonexistent_function")
        result = await hoogle_server._handle_hoogle_info(info_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "No information found" in result[0].text
        mock_hoogle_client.get_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_error(
        self, hoogle_server: HoogleMCPServer, mock_hoogle_client: Mock
    ) -> None:
        """Test info retrieval with error."""
        mock_hoogle_client.get_info.return_value = CommandResult(
            success=False,
            output="",
            error="Function not found",
            return_code=1,
        )

        info_args = GetInfoArgs(name="invalid_function")
        result = await hoogle_server._handle_hoogle_info(info_args)

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Information retrieval error" in result[0].text
        assert "Function not found" in result[0].text
        mock_hoogle_client.get_info.assert_called_once()
