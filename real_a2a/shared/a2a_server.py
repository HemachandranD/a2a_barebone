"""Small helpers to build and run an A2A service in one line."""

from typing import List, Optional, Sequence

import uvicorn
from starlette.applications import Starlette
from starlette.routing import BaseRoute

from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandlerV2
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill


def build_agent_card(
    *,
    name: str,
    description: str,
    url: str,
    skills: Sequence[AgentSkill],
    version: str = "0.1.0",
) -> AgentCard:
    return AgentCard(
        name=name,
        description=description,
        version=version,
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(protocol_binding="JSONRPC", url=url),
        ],
        skills=list(skills),
    )


def build_a2a_app(
    *,
    agent_card: AgentCard,
    executor: AgentExecutor,
    extra_routes: Optional[List[BaseRoute]] = None,
) -> Starlette:
    handler = DefaultRequestHandlerV2(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    routes: List[BaseRoute] = []
    routes.extend(
        create_agent_card_routes(agent_card, card_url="/public_agent_card")
    )
    routes.extend(create_jsonrpc_routes(handler, "/"))
    if extra_routes:
        routes.extend(extra_routes)
    return Starlette(routes=routes)


def run_a2a_service(
    *,
    agent_card: AgentCard,
    executor: AgentExecutor,
    host: str,
    port: int,
    extra_routes: Optional[List[BaseRoute]] = None,
) -> None:
    app = build_a2a_app(
        agent_card=agent_card,
        executor=executor,
        extra_routes=extra_routes,
    )
    uvicorn.run(app, host=host, port=port)
