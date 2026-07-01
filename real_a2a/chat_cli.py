"""Interactive CLI to chat with the Admin agent over A2A.

Assumes ``run_all.py`` (or at least the admin service) is already running.
"""

import asyncio
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from real_a2a.shared import config
from real_a2a.shared.a2a_client import call_agent


EXIT_TOKENS = {"exit", "quit", ":q"}


def _print_banner() -> None:
    print("=" * 60)
    print(" Admin agent chat CLI")
    print(f" Talking to: {config.ADMIN_BASE_URL}")
    print(" Type 'exit', 'quit', ':q', or Ctrl+C to leave.")
    print("=" * 60)


async def _prompt(prompt_text: str) -> str:
    return await asyncio.to_thread(input, prompt_text)


async def _chat_loop() -> None:
    _print_banner()
    while True:
        try:
            message = (await _prompt("\nyou> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not message:
            continue
        if message.lower() in EXIT_TOKENS:
            return

        try:
            reply = await call_agent(config.ADMIN_BASE_URL, message)
        except Exception as exc:
            reply = f"[error] {exc}"

        print(f"\nadmin>\n{reply}")


def main() -> None:
    try:
        asyncio.run(_chat_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
