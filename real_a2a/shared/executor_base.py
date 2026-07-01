"""Reusable ``AgentExecutor`` that wraps a callable returning text."""

from typing import Awaitable, Callable, Union

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)


InvokeFn = Callable[[str], Union[str, Awaitable[str]]]


class SimpleAgentExecutor(AgentExecutor):
    """Turns any ``async invoke(query: str) -> str`` callable into an A2A executor."""

    def __init__(self, invoke: InvokeFn, working_message: str = "Processing..."):
        self._invoke = invoke
        self._working_message = working_message

    async def _run(self, query: str) -> str:
        result = self._invoke(query)
        if hasattr(result, "__await__"):
            result = await result  # type: ignore[assignment]
        return str(result)

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message(self._working_message),
        )

        query = get_message_text(context.message)
        try:
            answer = (
                await self._run(query) if query else "No text input was provided."
            )
        except Exception as exc:  # surfaces the failure back to the caller
            answer = f"Agent error: {exc}"
            await updater.add_artifact(
                parts=[new_text_part(text=answer, media_type="text/plain")]
            )
            await updater.update_status(
                state=TaskState.TASK_STATE_FAILED,
                message=new_text_message("Request failed."),
            )
            return

        await updater.add_artifact(
            parts=[new_text_part(text=answer, media_type="text/plain")]
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message("Request completed."),
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await updater.update_status(
            state=TaskState.TASK_STATE_FAILED,
            message=new_text_message("Request cancelled."),
        )
