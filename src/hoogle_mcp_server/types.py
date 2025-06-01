"""Type definitions for Hoogle MCP Server.

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

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Literal,
    Optional,
    Annotated,
)

from mcp.types import TextContent
from pydantic import BaseModel, Field

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class CommandResult(BaseModel):
    """Result of executing a hoogle command."""

    success: bool
    output: str
    error: Optional[str] = None
    return_code: Optional[int] = None


class SearchArgs(BaseModel):
    """Arguments for hoogle_search tool."""

    query: str
    max_results: Optional[
        Annotated[
            int, Field(ge=1, le=100, description="Maximum number of results (1-100)")
        ]
    ] = None


class GetInfoArgs(BaseModel):
    """Arguments for hoogle_info tool."""

    name: str


ToolResponse = list[TextContent]
ToolHandler = Callable[[Dict[str, Any]], Awaitable[ToolResponse]]
