from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import TaskStatusUpdateEvent, TaskArtifactUpdateEvent, TaskState, TaskStatus
from a2a.helpers import new_text_message, new_text_artifact, new_task_from_user_message


class HelloWorldAgent:
    """Hello World Agent."""

    async def invoke(self) -> str:
        """Invoke the Hello World agent to generate a response."""
        return 'Hello, World!'


class HelloWorldAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = HelloWorldAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent process and enqueue the final response."""
        task = context.current_task or new_task_from_user_message(
            context.message
        )

        await event_queue.enqueue_event(task)

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state=TaskState.TASK_STATE_WORKING,
                    message=new_text_message('Processing request...'),
                ),
                )
            )

        result = await self.agent.invoke()

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                artifact=new_text_artifact(name='result', text=result),
            )
        )

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                state=TaskStatus(
                    state=TaskState.TASK_STATE_COMPLETED,

                )
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                state=TaskStatus(
                    state=TaskState.TASK_STATE_CANCELLED,
                )
            )
        )
