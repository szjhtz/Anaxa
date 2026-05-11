"""Configuration for automatic thread title generation."""

from pydantic import BaseModel, Field


class TitleConfig(BaseModel):
    """Configuration for automatic thread title generation."""

    enabled: bool = Field(
        default=True,
        description="Whether to enable automatic title generation",
    )
    max_words: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Maximum number of words in the generated title",
    )
    max_chars: int = Field(
        default=90,
        ge=10,
        le=200,
        description="Maximum number of characters in the generated title",
    )
    model_name: str | None = Field(
        default=None,
        description="Model name to use for title generation (None = use default model)",
    )
    prompt_template: str = Field(
        default=(
            "Write one concise, specific one-line conversation label for this completed exchange.\n"
            "It should summarize the actual topic, task object, deliverable, method, or current blocker. "
            "Prefer concrete labels such as 'LaTeX PDF 编译排错' over generic descriptions. "
            "Keep it within {max_chars} characters when possible.\n"
            "Do not output generic prefixes or labels such as 'Here is a summary of the conversation to date', "
            "'Conversation Summary', 'Summary', 'Research', 'Help', or 'Chat'. "
            "Do not mention roles, instructions, reasoning, or the word title.\n\n"
            "User message:\n{user_msg}\n\n"
            "Assistant summary:\n{assistant_msg}\n\n"
            "Return only the one-line label, with no quotes or explanation."
        ),
        description="Prompt template for title generation",
    )


# Global configuration instance
_title_config: TitleConfig = TitleConfig()


def get_title_config() -> TitleConfig:
    """Get the current title configuration."""
    return _title_config


def set_title_config(config: TitleConfig) -> None:
    """Set the title configuration."""
    global _title_config
    _title_config = config


def load_title_config_from_dict(config_dict: dict) -> None:
    """Load title configuration from a dictionary."""
    global _title_config
    _title_config = TitleConfig(**config_dict)
