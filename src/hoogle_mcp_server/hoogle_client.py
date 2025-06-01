"""Hoogle client for executing hoogle commands.

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

import asyncio
import logging
from typing import List

from .types import CommandResult, GetInfoArgs, SearchArgs


class HoogleClient:
    """Client for executing hoogle commands."""

    def __init__(self, hoogle_path: str, timeout_seconds: int = 5) -> None:
        """Initialize the hoogle client.

        Args:
            hoogle_path: Path to the hoogle executable
            timeout_seconds: Command execution timeout in seconds
        """
        self.hoogle_path = hoogle_path
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(__name__)

    async def _execute_process_with_timeout(
        self, process: asyncio.subprocess.Process
    ) -> CommandResult:
        """Execute process with timeout handling."""
        self.logger.debug(f"Executing process with PID: {process.pid}")

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout_seconds
            )

            if process.returncode is None:
                self.logger.error(
                    "Process did not complete properly (returncode is None)"
                )
                return {
                    "success": False,
                    "error": "Process did not complete properly (returncode is None)",
                    "output": stdout.decode("utf-8") if stdout else "",
                    "return_code": None,
                }

            self.logger.debug(
                f"Process completed with return code: {process.returncode}"
            )

            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8") if stdout else "",
                "error": (
                    stderr.decode("utf-8")
                    if stderr and process.returncode != 0
                    else None
                ),
                "return_code": process.returncode,
            }

        except asyncio.TimeoutError:
            self.logger.warning(
                f"Process timed out after {self.timeout_seconds} seconds"
            )
            try:
                process.kill()
                await process.wait()
                self.logger.debug("Process killed successfully")
            except ProcessLookupError:
                self.logger.debug("Process already terminated")
                pass

            return {
                "success": False,
                "error": (
                    f"Command execution timed out ({self.timeout_seconds} seconds)"
                ),
                "output": "",
                "return_code": None,
            }

    async def run_command(self, args: List[str]) -> CommandResult:
        """Execute hoogle command asynchronously and return the result."""
        self.logger.info(f"Running hoogle command with args: {args}")

        try:
            cmd = [self.hoogle_path] + args
            self.logger.debug(f"Full command: {' '.join(cmd)}")

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            result = await self._execute_process_with_timeout(process)

            if result["success"]:
                self.logger.info("Hoogle command executed successfully")
                self.logger.debug(f"Output length: {len(result['output'])} characters")
            else:
                self.logger.error(f"Hoogle command failed: {result['error']}")

            return result

        except Exception as e:
            self.logger.error(f"Command execution error: {str(e)}")
            return {
                "success": False,
                "error": f"Command execution error: {str(e)}",
                "output": "",
                "return_code": None,
            }

    async def search(self, search_args: SearchArgs) -> CommandResult:
        """Search for functions and types using hoogle."""
        query = search_args.get("query", "")
        max_results = search_args.get("max_results", 10)

        self.logger.info(
            f"Searching hoogle: query='{query}', max_results={max_results}"
        )

        args = ["search"]
        args.append(f"--count={max_results}")
        args.append("--")
        args.append(query)

        return await self.run_command(args)

    async def get_info(self, info_args: GetInfoArgs) -> CommandResult:
        """Get detailed information about a specific function or type."""
        name = info_args.get("name", "")

        self.logger.info(f"Getting hoogle info: name='{name}'")

        args = ["search", "-i", "--", name]
        return await self.run_command(args)
