"""HoogleMCPServer class definition.

Copyright (C) 2025  Hiroki Tokunaga

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
from typing import Any, Dict

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import TextContent, Tool
from pydantic import ValidationError

from .hoogle_client import HoogleClient
from .types import (
    GetInfoArgs,
    LogLevel,
    SearchArgs,
    ToolResponse,
    MAX_QUERY_LENGTH,
    get_version,
)


class HoogleMCPServer:
    """MCP Server for Hoogle search functionality."""

    def __init__(self, hoogle_client: HoogleClient, logger: logging.Logger) -> None:
        """Initialize the server with a Hoogle client and logger."""
        self.hoogle_client = hoogle_client
        self.logger = logger
        self.server: Server[str] = Server("hoogle-mcp-server")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup MCP server handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="hoogle_search",
                    description=(
                        "Search for function and type definitions using the "
                        "Haskell API search engine Hoogle"
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": (
                                    "Search query (function name, type signature, or keywords)"
                                ),
                                "maxLength": MAX_QUERY_LENGTH,
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 100,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="hoogle_info",
                    description=(
                        "Get detailed information about a specific function or type"
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": (
                                    "Function name or type name to get detailed information for"
                                ),
                                "maxLength": MAX_QUERY_LENGTH,
                            }
                        },
                        "required": ["name"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any] | None
        ) -> ToolResponse:
            """Handle tool calls."""
            self.logger.info(f"Tool call received: {name}")
            self.logger.debug(f"Tool arguments: {arguments}")

            if arguments is None:
                arguments = {}

            try:
                self.logger.debug(f"Executing tool {name} with arguments: {arguments}")

                match name:
                    case "hoogle_search":
                        search_args = SearchArgs(**arguments)
                        result = await self._handle_hoogle_search(search_args)
                    case "hoogle_info":
                        info_args = GetInfoArgs(**arguments)
                        result = await self._handle_hoogle_info(info_args)
                    case _:
                        self.logger.error(f"Unknown tool requested: {name}")
                        return [
                            TextContent(
                                type="text", text=f"Error: Unknown tool '{name}'"
                            )
                        ]

                self.logger.info(f"Tool {name} executed successfully")
                return result
            except ValidationError as e:
                error_details = []
                for error in e.errors():
                    field = error.get("loc", ("unknown",))[-1]
                    msg = error.get("msg", "Invalid value")
                    error_details.append(f"{field}: {msg}")

                error_message = (
                    f"Validation error for {name}: {'; '.join(error_details)}"
                )
                self.logger.warning(error_message)
                return [TextContent(type="text", text=f"Error: {error_message}")]
            except Exception as e:
                self.logger.error(f"Error executing tool {name}: {str(e)}")
                return [
                    TextContent(
                        type="text", text=f"Error executing tool '{name}': {str(e)}"
                    )
                ]

    async def _handle_hoogle_search(self, arguments: SearchArgs) -> ToolResponse:
        """Handle hoogle_search tool calls."""
        query = arguments.query
        max_results = arguments.max_results or 10

        self.logger.info(
            f"Handling hoogle_search: query='{query}', max_results={max_results}"
        )

        if not query:
            self.logger.warning("Search query not specified")
            return [TextContent(type="text", text="Error: Search query not specified")]

        result = await self.hoogle_client.search(arguments)

        if not result.success:
            response_text = f"Search error: {result.error}\n"
            response_text += f"Output: {result.output}" if result.output else ""
            return [TextContent(type="text", text=response_text)]

        response_text = f"Hoogle search results (query: '{query}'):\n\n"

        if result.output:
            response_text += result.output
            self.logger.debug(
                f"Search returned {len(result.output.splitlines())} lines"
            )
        else:
            response_text += "No search results found."
            self.logger.info("No search results found")

        return [TextContent(type="text", text=response_text)]

    async def _handle_hoogle_info(self, arguments: GetInfoArgs) -> ToolResponse:
        """Handle hoogle_info tool calls."""
        name_param = arguments.name

        self.logger.info(f"Handling hoogle_info: name='{name_param}'")

        if not name_param:
            self.logger.warning("Function name or type name not specified")
            return [
                TextContent(
                    type="text", text="Error: Function name or type name not specified"
                )
            ]

        result = await self.hoogle_client.get_info(arguments)

        if not result.success:
            response_text = f"Information retrieval error: {result.error}\n"
            response_text += f"Output: {result.output}" if result.output else ""
            return [TextContent(type="text", text=response_text)]

        response_text = f"Detailed information for '{name_param}':\n\n"

        if result.output:
            response_text += result.output
            self.logger.debug(f"Info returned {len(result.output.splitlines())} lines")
        else:
            response_text += "No information found."
            self.logger.info("No information found")

        return [TextContent(type="text", text=response_text)]

    async def run(self, log_level: LogLevel = "INFO") -> None:
        """Run the MCP server."""
        from .logger import setup_logging

        setup_logging(log_level)
        self.logger.info("Starting Hoogle MCP Server")

        from mcp.server.stdio import stdio_server

        self.logger.info("Starting stdio server")
        async with stdio_server() as (read_stream, write_stream):
            self.logger.info("Server running, waiting for requests...")
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="hoogle-mcp-server",
                    server_version=get_version(),
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
