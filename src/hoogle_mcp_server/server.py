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
import sys

from .hoogle_client import HoogleClient
from .hoogle_mcp_server import HoogleMCPServer
from .logger import get_logger, setup_logging
from .types import LogLevel, get_version

logger = get_logger(__name__)


async def main(log_level: LogLevel = "INFO") -> None:
    """Main server function."""
    setup_logging(log_level)

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

    server_logger = get_logger("hoogle_mcp_server.server")
    server = HoogleMCPServer(hoogle_client, server_logger)
    await server.run(log_level)


def parse_cli_arguments() -> LogLevel:
    """Parse command line arguments and return the log level.

    When both --verbose and --log-level are specified, --verbose takes precedence
    and the log level will be set to DEBUG regardless of the --log-level value.
    """
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
        help=(
            "Enable verbose logging (equivalent to --log-level DEBUG). "
            "If specified with --log-level, this option takes precedence."
        ),
    )

    args = parser.parse_args()

    return "DEBUG" if args.verbose else args.log_level


def cli_main() -> None:
    """CLI entry point that runs the async main function."""
    log_level = parse_cli_arguments()

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
