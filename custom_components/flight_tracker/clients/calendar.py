"""iCal feed client."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp import ClientSession


class IcalCalendarClient:
    """Small client for downloading an iCal feed."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the client."""
        self._session = session

    async def async_fetch(self, url: str) -> str:
        """Download iCal text from a URL."""
        async with self._session.get(url, timeout=20) as response:
            response.raise_for_status()
            return await response.text()
