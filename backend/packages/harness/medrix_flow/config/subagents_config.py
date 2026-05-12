"""Configuration for the subagent system loaded from config.yaml."""

import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MIN_SUBAGENT_POOL_SIZE = 1
DEFAULT_SUBAGENT_POOL_SIZE = 3
MAX_SUBAGENT_POOL_SIZE = 16


class SubagentOverrideConfig(BaseModel):
    """Per-agent configuration overrides."""

    timeout_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Timeout in seconds for this subagent (None = use global default)",
    )


class SubagentsAppConfig(BaseModel):
    """Configuration for the subagent system."""

    pool_size: int = Field(
        default=DEFAULT_SUBAGENT_POOL_SIZE,
        ge=MIN_SUBAGENT_POOL_SIZE,
        le=MAX_SUBAGENT_POOL_SIZE,
        description="Maximum number of subagents that may run concurrently",
    )
    timeout_seconds: int = Field(
        default=900,
        ge=1,
        description="Default timeout in seconds for all subagents (default: 900 = 15 minutes)",
    )
    agents: dict[str, SubagentOverrideConfig] = Field(
        default_factory=dict,
        description="Per-agent configuration overrides keyed by agent name",
    )

    def get_timeout_for(self, agent_name: str) -> int:
        """Get the effective timeout for a specific agent.

        Args:
            agent_name: The name of the subagent.

        Returns:
            The timeout in seconds, using per-agent override if set, otherwise global default.
        """
        override = self.agents.get(agent_name)
        if override is not None and override.timeout_seconds is not None:
            return override.timeout_seconds
        return self.timeout_seconds


_subagents_config: SubagentsAppConfig = SubagentsAppConfig()


def get_subagents_app_config() -> SubagentsAppConfig:
    """Get the current subagents configuration."""
    return _subagents_config


def load_subagents_config_from_dict(config_dict: dict) -> None:
    """Load subagents configuration from a dictionary."""
    global _subagents_config
    _subagents_config = SubagentsAppConfig(**config_dict)

    overrides_summary = {name: f"{override.timeout_seconds}s" for name, override in _subagents_config.agents.items() if override.timeout_seconds is not None}
    if overrides_summary:
        logger.info(
            "Subagents config loaded: pool_size=%s, default timeout=%ss, per-agent overrides=%s",
            _subagents_config.pool_size,
            _subagents_config.timeout_seconds,
            overrides_summary,
        )
    else:
        logger.info(
            "Subagents config loaded: pool_size=%s, default timeout=%ss, no per-agent overrides",
            _subagents_config.pool_size,
            _subagents_config.timeout_seconds,
        )
