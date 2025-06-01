"""HooglePath class for managing hoogle executable path.

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

from typing import Optional


class HooglePath:
    """Manages the hoogle executable path."""

    def __init__(self) -> None:
        self._path: Optional[str] = None

    def init(self, path: str) -> None:
        """Initialize the hoogle path."""
        self._path = path

    def get(self) -> str:
        """Get the hoogle path, raising an error if not initialized."""
        if self._path is None:
            raise RuntimeError(
                "Hoogle path not initialized. Server startup may have failed."
            )
        return self._path
