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
import shutil
import subprocess
from importlib import metadata
from typing import Any, Dict, List

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

HOOGLE_COMMAND_TIMEOUT_SECONDS = 30

server: Server = Server("hoogle-mcp-server")


def get_version() -> str:
    """Get package version from metadata."""
    try:
        return metadata.version("hoogle-mcp-server")
    except metadata.PackageNotFoundError:
        return "(no version info)"


def run_hoogle_command(args: List[str]) -> Dict[str, Any]:
    """Execute hoogle command and return the result."""
    try:
        # Check if hoogle command is available using shutil.which
        hoogle_path = shutil.which("hoogle")
        if not hoogle_path:
            return {
                "success": False,
                "error": (
                    "hoogle command not found. "
                    "Please check your Haskell platform installation."
                ),
                "output": "",
            }

        cmd = [hoogle_path] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=HOOGLE_COMMAND_TIMEOUT_SECONDS,
            shell=False,
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "return_code": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": (
                f"Command execution timed out "
                f"({HOOGLE_COMMAND_TIMEOUT_SECONDS} seconds)"
            ),
            "output": "",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Command execution error: {str(e)}",
            "output": "",
        }


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
                    }
                },
                "required": ["name"],
            },
        ),
    ]


async def handle_hoogle_search(
    arguments: dict,
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle hoogle_search tool calls."""
    query = arguments.get("query", "")
    max_results = arguments.get("max_results", 10)

    if not query:
        return [TextContent(type="text", text="Error: Search query not specified")]

    args = ["search"]
    args.extend(["--count", str(max_results)])
    args.append("--")
    args.append(query)

    result = run_hoogle_command(args)

    if result["success"]:
        response_text = f"Hoogle search results (query: '{query}'):\n\n"
        if result["output"]:
            response_text += result["output"]
        else:
            response_text += "No search results found."
    else:
        response_text = f"Search error: {result['error']}\n"
        if result["output"]:
            response_text += f"Output: {result['output']}"

    return [TextContent(type="text", text=response_text)]


async def handle_hoogle_info(
    arguments: dict,
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle hoogle_info tool calls."""
    name_param = arguments.get("name", "")

    if not name_param:
        return [
            TextContent(
                type="text", text="Error: Function name or type name not specified"
            )
        ]

    args = ["search", "-i", "--", name_param]
    result = run_hoogle_command(args)

    if result["success"]:
        response_text = f"Detailed information for '{name_param}':\n\n"
        if result["output"]:
            response_text += result["output"]
        else:
            response_text += "No information found."
    else:
        response_text = f"Information retrieval error: {result['error']}\n"
        if result["output"]:
            response_text += f"Output: {result['output']}"

    return [TextContent(type="text", text=response_text)]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""
    if arguments is None:
        arguments = {}

    if name == "hoogle_search":
        return await handle_hoogle_search(arguments)
    elif name == "hoogle_info":
        return await handle_hoogle_info(arguments)
    else:
        return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]


async def main():
    """Main server function."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
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


def cli_main():
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

    # Parse arguments (variable unused, but parser.parse_args() needed)
    parser.parse_args()

    # Run the server
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
