"""Shared runtime configuration for LangGraph agents."""

from collections.abc import Hashable
from typing import Any

from langchain_core.runnables import RunnableConfig

AGENT_RECURSION_LIMIT = 1000


def agent_config(thread_id: Hashable | None = None) -> RunnableConfig:
    """Build a LangGraph config with a high recursion limit."""
    config: dict[str, Any] = {"recursion_limit": AGENT_RECURSION_LIMIT}
    if thread_id is not None:
        config["configurable"] = {"thread_id": thread_id}
    return config  # type: ignore
