import httpx
import asyncio
import uuid

from a2a.client import A2ACardResolver, create_client, ClientConfig
from a2a.types.a2a_pb2 import SendMessageRequest, Role
from a2a.helpers import new_text_message

BASE_URL = "http://localhost:9999"

async def main():
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, 
        base_url=BASE_URL,
        agent_card_path='/public_agent_card')

        try:
            public_agent_card = await resolver.get_agent_card()
            print(public_agent_card)
            
        except Exception as e:
            raise RuntimeError(f"Error getting public agent card: {e}")

        print('\nInitializing a streaming client.')
        config = ClientConfig(streaming=True)  # Streaming
        client = await create_client(agent=public_agent_card, client_config=config)

        message = new_text_message("Hello", role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        print('Response:')
        async for chunk in client.send_message(request):
            print(chunk)

if __name__ == "__main__":
    asyncio.run(main())