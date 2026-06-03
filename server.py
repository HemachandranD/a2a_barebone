import uvicorn
from starlette.applications import Starlette
from a2a.server.request_handlers import DefaultRequestHandlerV2, DefaultRequestHandlerV2
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.server.tasks import InMemoryTaskStore
from executor import HelloWorldAgentExecutor

def setup_skills():

    skill = AgentSkill(
        id='hello_world',
        name='Returns hello world',
        description='just returns hello world',
        tags=['hello world'],
        examples=['hi', 'hello world'],
    )

    extended_skill = AgentSkill(
        id='super_hello_world',
        name='Returns a SUPER Hello World',
        description='A more enthusiastic greeting, only for authenticated users.',
        tags=['hello world', 'super', 'extended'],
        examples=['super hi', 'give me a super hello'],
    )

    return skill, extended_skill


def setup_agent_card(skill, extended_skill):

    public_agent_card = AgentCard(
        name='Hello World Agent',
        description='Just a hello world agent',
        version='0.0.1',
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
        capabilities=AgentCapabilities(
            streaming=True, extended_agent_card=True
        ),
        skills=[skill],  # Only the basic skill for the public card
    )

    extended_agent_card = AgentCard(
        name='Hello World Agent - Extended Edition',
        description='The full-featured hello world agent for authenticated users.',
        version='0.0.2',
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
        capabilities=AgentCapabilities(
            streaming=True, extended_agent_card=True
        ),
        skills=[skill, extended_skill],  # Both skills for the extended card
    )

    return public_agent_card, extended_agent_card


def main():

    skill, extended_skill = setup_skills()
    public_agent_card, extended_agent_card = setup_agent_card(skill, extended_skill)
    

    request_handler= DefaultRequestHandlerV2(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=public_agent_card,
        extended_agent_card=extended_agent_card,
    )
    
    routes=[]
    routes.extend(create_agent_card_routes(public_agent_card, card_url='/public_agent_card'))
    routes.extend(create_jsonrpc_routes(request_handler, '/'))

    app = Starlette(routes=routes)

    uvicorn.run(app, host='127.0.0.1', port=9999, reload=True)


if __name__ == "__main__":
    main()