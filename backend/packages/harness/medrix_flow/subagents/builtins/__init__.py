"""Built-in subagent configurations."""

from .academic_researcher import ACADEMIC_RESEARCHER_CONFIG
from .bash_agent import BASH_AGENT_CONFIG
from .general_purpose import GENERAL_PURPOSE_CONFIG
from .visual_specialist import VISUAL_SPECIALIST_CONFIG

__all__ = [
    "GENERAL_PURPOSE_CONFIG",
    "BASH_AGENT_CONFIG",
    "ACADEMIC_RESEARCHER_CONFIG",
    "VISUAL_SPECIALIST_CONFIG",
]

# Registry of built-in subagents
BUILTIN_SUBAGENTS = {
    "general-purpose": GENERAL_PURPOSE_CONFIG,
    "bash": BASH_AGENT_CONFIG,
    "academic-researcher": ACADEMIC_RESEARCHER_CONFIG,
    "visual-specialist": VISUAL_SPECIALIST_CONFIG,
}
