"""Middleware to enforce maximum concurrent subagent tool calls per model response."""

import logging
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from medrix_flow.config.subagents_config import get_subagents_app_config

logger = logging.getLogger(__name__)

MIN_SUBAGENT_LIMIT = 1


def _clamp_subagent_limit(value: int, pool_size: int | None = None) -> int:
    """Clamp subagent limit to the configured worker pool."""
    effective_pool_size = pool_size if pool_size is not None else get_subagents_app_config().pool_size
    return max(MIN_SUBAGENT_LIMIT, min(effective_pool_size, value))


class SubagentLimitMiddleware(AgentMiddleware[AgentState]):
    """Truncates excess 'task' tool calls from a single model response.

    When an LLM generates more than max_concurrent parallel task tool calls
    in one response, this middleware keeps only the first max_concurrent and
    discards the rest. This is more reliable than prompt-based limits.

    Args:
        max_concurrent: Maximum number of concurrent subagent calls allowed.
            Defaults to subagents.pool_size. Clamped to [1, subagents.pool_size].
    """

    def __init__(self, max_concurrent: int | None = None):
        super().__init__()
        pool_size = get_subagents_app_config().pool_size
        self.max_concurrent = _clamp_subagent_limit(max_concurrent if max_concurrent is not None else pool_size, pool_size)

    def _truncate_task_calls(self, state: AgentState) -> dict | None:
        messages = state.get("messages", [])
        if not messages:
            return None

        last_msg = messages[-1]
        if getattr(last_msg, "type", None) != "ai":
            return None

        tool_calls = getattr(last_msg, "tool_calls", None)
        if not tool_calls:
            return None

        # Count task tool calls
        task_indices = [i for i, tc in enumerate(tool_calls) if tc.get("name") == "task"]
        if len(task_indices) <= self.max_concurrent:
            return None

        # Build set of indices to drop (excess task calls beyond the limit)
        indices_to_drop = set(task_indices[self.max_concurrent :])
        truncated_tool_calls = [tc for i, tc in enumerate(tool_calls) if i not in indices_to_drop]

        dropped_count = len(indices_to_drop)
        logger.warning(f"Truncated {dropped_count} excess task tool call(s) from model response (limit: {self.max_concurrent})")

        # Replace the AIMessage with truncated tool_calls (same id triggers replacement)
        updated_msg = last_msg.model_copy(update={"tool_calls": truncated_tool_calls})
        return {"messages": [updated_msg]}

    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._truncate_task_calls(state)

    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._truncate_task_calls(state)
