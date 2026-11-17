import ssl
from pathlib import Path
from typing import Any

import httpx


def make_ssl_context(ca_cert: Path) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=str(ca_cert))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


class ServerClient:
    def __init__(
        self,
        base_url: str,
        ca_cert: Path | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        verify: ssl.SSLContext | bool = make_ssl_context(ca_cert) if ca_cert else True
        self._client = httpx.AsyncClient(
            base_url=base_url, verify=verify, transport=transport, timeout=timeout
        )

    async def health(self) -> Any:
        response = await self._client.get("/api/health")
        response.raise_for_status()
        return response.json()

    async def aclose(self) -> None:
        await self._client.aclose()
