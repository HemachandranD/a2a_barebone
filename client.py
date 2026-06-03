import httpx
import asyncio
from a2a.client import A2ACardResolver

BASE_URL = "http://localhost:9999"

async def main():
    async with httpx.AsyncClient() as client:
        resolver = A2ACardResolver(httpx_client=client, 
        base_url=BASE_URL,
        agent_card_path='/public_agent_card')

        public_agent_card = await resolver.get_agent_card()

        return public_agent_card

if __name__ == "__main__":
    public_agent_card = asyncio.run(main())
    print(public_agent_card)