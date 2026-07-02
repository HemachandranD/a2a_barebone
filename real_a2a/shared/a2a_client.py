"""Thin async helper to call another A2A service and return text."""

import httpx

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_stream_response_text, new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest
from opentelemetry.propagate import inject


class _PropagatingTransport(httpx.AsyncHTTPTransport):
    """Injects W3C traceparent/tracestate on every outbound call, without
    opening a per-request span (http_transport_spans: none -- the meaningful
    spans are the framework instrumentor's, not the raw httpx call)."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        inject(request.headers)
        return await super().handle_async_request(request)


async def call_agent(base_url: str, text: str, *, timeout: float = 300.0) -> str:
    """Send ``text`` to the A2A service at ``base_url`` and return the response text."""
    async with httpx.AsyncClient(timeout=timeout, transport=_PropagatingTransport()) as http:
        resolver = A2ACardResolver(
            httpx_client=http,
            base_url=base_url,
            agent_card_path="/public_agent_card",
        )
        card = await resolver.get_agent_card()
        client = await create_client(
            agent=card,
            client_config=ClientConfig(streaming=True, httpx_client=http),
        )

        message = new_text_message(text, role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        collected: list[str] = []
        async for chunk in client.send_message(request):
            piece = get_stream_response_text(chunk)
            if piece:
                collected.append(piece)

        seen: set[str] = set()
        unique: list[str] = []
        for piece in collected:
            if piece not in seen:
                seen.add(piece)
                unique.append(piece)
        return "\n".join(unique).strip()
