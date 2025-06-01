"""Hoogle MCP Server implementation.

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

import argparse
import asyncio
import logging
import shutil
import sys
from importlib import metadata
from typing import Any, Dict

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import TextContent, Tool

from .hoogle_client import HoogleClient
from .types import LogLevel, ToolHandler, ToolResponse

MAX_QUERY_LENGTH = 500

server: Server[str] = Server("hoogle-mcp-server")
hoogle_client: HoogleClient | None = None
logger = logging.getLogger(__name__)


def setup_logging(log_level: LogLevel = "INFO") -> None:
    """Setup logging configuration with specified log level."""

    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Logging initialized with level: %s", log_level.upper())


def get_version() -> str:
    """Get package version from metadata."""
    try:
        return metadata.version("hoogle-mcp-server")
    except metadata.PackageNotFoundError:
        return "(no version info)"


@server.list_tools()
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
            description=("Get detailed information about a specific function or type"),
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


async def handle_hoogle_search(
    arguments: Dict[str, Any],
) -> ToolResponse:
    """Handle hoogle_search tool calls."""
    if hoogle_client is None:
        return [TextContent(type="text", text="Error: Hoogle client not initialized")]

    query = arguments.get("query", "")
    max_results = arguments.get("max_results", 10)

    logger.info(f"Handling hoogle_search: query='{query}', max_results={max_results}")

    if not query:
        logger.warning("Search query not specified")
        return [TextContent(type="text", text="Error: Search query not specified")]

    result = await hoogle_client.search(query, max_results)

    if not result["success"]:
        response_text = f"Search error: {result['error']}\n"
        response_text += f"Output: {result['output']}" if result["output"] else ""
        return [TextContent(type="text", text=response_text)]

    response_text = f"Hoogle search results (query: '{query}'):\n\n"

    if result["output"]:
        response_text += result["output"]
        logger.debug(f"Search returned {len(result['output'].splitlines())} lines")
    else:
        response_text += "No search results found."
        logger.info("No search results found")

    return [TextContent(type="text", text=response_text)]


async def handle_hoogle_info(
    arguments: Dict[str, Any],
) -> ToolResponse:
    """Handle hoogle_info tool calls."""
    if hoogle_client is None:
        return [TextContent(type="text", text="Error: Hoogle client not initialized")]

    name_param = arguments.get("name", "")

    logger.info(f"Handling hoogle_info: name='{name_param}'")

    if not name_param:
        logger.warning("Function name or type name not specified")
        return [
            TextContent(
                type="text", text="Error: Function name or type name not specified"
            )
        ]

    result = await hoogle_client.get_info(name_param)

    if not result["success"]:
        response_text = f"Information retrieval error: {result['error']}\n"
        response_text += f"Output: {result['output']}" if result["output"] else ""
        return [TextContent(type="text", text=response_text)]

    response_text = f"Detailed information for '{name_param}':\n\n"

    if result["output"]:
        response_text += result["output"]
        logger.debug(f"Info returned {len(result['output'].splitlines())} lines")
    else:
        response_text += "No information found."
        logger.info("No information found")

    return [TextContent(type="text", text=response_text)]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any] | None) -> ToolResponse:
    """Handle tool calls."""
    logger.info(f"Tool call received: {name}")
    logger.debug(f"Tool arguments: {arguments}")

    if arguments is None:
        arguments = {}

    tool_handlers: Dict[str, ToolHandler] = {
        "hoogle_search": handle_hoogle_search,
        "hoogle_info": handle_hoogle_info,
    }

    handler = tool_handlers.get(name)
    if not handler:
        logger.error(f"Unknown tool requested: {name}")
        return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

    try:
        logger.debug(f"Executing tool {name} with arguments: {arguments}")
        result = await handler(arguments)
        logger.info(f"Tool {name} executed successfully")
        return result
    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}")
        return [
            TextContent(type="text", text=f"Error executing tool '{name}': {str(e)}")
        ]


async def main(log_level: LogLevel = "INFO") -> None:
    """Main server function."""
    global hoogle_client

    setup_logging(log_level)
    logger.info("Starting Hoogle MCP Server")

    found_hoogle_path = shutil.which("hoogle")
    if not found_hoogle_path:
        error_msg = (
            "Error: hoogle command not found. "
            "Please install the Haskell platform and hoogle before running this server."
        )
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        return

    hoogle_client = HoogleClient(found_hoogle_path)
    logger.info(f"Hoogle found at: {found_hoogle_path}")

    from mcp.server.stdio import stdio_server

    logger.info("Starting stdio server")
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Server running, waiting for requests...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="hoogle-mcp-server",
                server_version=get_version(),
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cli_main() -> None:
    """CLI entry point that runs the async main function."""
    parser = argparse.ArgumentParser(
        prog="hoogle-mcp-server",
        description="MCP server for accessing Hoogle search functionality",
        epilog=(
            "This server provides tools to search Haskell functions "
            "and types using Hoogle."
        ),
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {get_version()}"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (equivalent to --log-level DEBUG)",
    )

    args = parser.parse_args()

    # If verbose is specified, override log level to DEBUG
    log_level: LogLevel = "DEBUG" if args.verbose else args.log_level

    try:
        asyncio.run(main(log_level=log_level))
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
        print("\nServer shutdown.", file=sys.stderr)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
