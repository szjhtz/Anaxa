from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, TypedDict

PlanStatus = Literal["draft", "awaiting_approval", "needs_revision", "approved", "executing", "completed", "blocked"]


class PlanRevision(TypedDict, total=False):
    revision_number: int
    source: str
    note: str
    status: PlanStatus
    updated_at: str


class PlanState(TypedDict, total=False):
    summary: str
    phases: list[str]
    deliverables: list[str]
    open_questions: list[str]
    acceptance_criteria: list[str]
    risk_points: list[str]
    revision_count: int
    status: PlanStatus
    updated_at: str
    revisions: list[PlanRevision]


PLAN_PENDING_STATUSES: frozenset[PlanStatus] = frozenset({"draft", "awaiting_approval", "needs_revision"})
PLAN_ACTIVE_STATUSES: frozenset[PlanStatus] = frozenset({"approved", "executing", "completed"})
PLAN_LOCKED_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "bash",
        "task",
        "experiment_lab",
        "matlab_execution",
        "manuscript_export",
        "present_files",
        "research_assistant",
        "setup_agent",
        "str_replace",
        "write_file",
    }
)


def normalize_plan_items(items: list[str] | None) -> list[str]:
    if not items:
        return []
    cleaned: list[str] = []
    for item in items:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            cleaned.append(text)
    return cleaned


def normalize_plan_status(status: str | None) -> PlanStatus:
    if status in PLAN_PENDING_STATUSES | PLAN_ACTIVE_STATUSES | frozenset({"blocked"}):
        return status  # type: ignore[return-value]
    return "awaiting_approval"


def plan_is_approved(plan: PlanState | None) -> bool:
    if not plan:
        return False
    return normalize_plan_status(plan.get("status")) in PLAN_ACTIVE_STATUSES


def format_plan_for_prompt(plan: PlanState) -> str:
    revisions = list(plan.get("revisions") or [])[-5:]
    lines = [
        "<thread_plan>",
        f"status: {plan.get('status') or 'awaiting_approval'}",
        f"revision_count: {int(plan.get('revision_count') or 0)}",
        f"updated_at: {plan.get('updated_at') or '—'}",
        f"summary: {plan.get('summary') or '—'}",
        "phases:",
    ]
    phases = normalize_plan_items(plan.get("phases"))
    lines.extend(f"- {item}" for item in phases or ["—"])
    lines.append("deliverables:")
    deliverables = normalize_plan_items(plan.get("deliverables"))
    lines.extend(f"- {item}" for item in deliverables or ["—"])
    lines.append("open_questions:")
    open_questions = normalize_plan_items(plan.get("open_questions"))
    lines.extend(f"- {item}" for item in open_questions or ["—"])
    lines.append("acceptance_criteria:")
    criteria = normalize_plan_items(plan.get("acceptance_criteria"))
    lines.extend(f"- {item}" for item in criteria or ["—"])
    lines.append("risk_points:")
    risks = normalize_plan_items(plan.get("risk_points"))
    lines.extend(f"- {item}" for item in risks or ["—"])
    lines.append("revisions:")
    if revisions:
        for revision in revisions:
            note = revision.get("note") or "—"
            source = revision.get("source") or "agent"
            revision_number = revision.get("revision_number") or "?"
            updated_at = revision.get("updated_at") or "—"
            lines.append(f"- #{revision_number} [{source}] {updated_at}: {note}")
    else:
        lines.append("- —")
    lines.append("</thread_plan>")
    return "\n".join(lines)


def build_plan_state(
    *,
    existing: PlanState | None,
    summary: str,
    phases: list[str] | None,
    deliverables: list[str] | None,
    open_questions: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    risk_points: list[str] | None = None,
    status: str | None = None,
    source: str = "agent",
    note: str | None = None,
) -> PlanState:
    revision_count = int((existing or {}).get("revision_count") or 0) + 1
    timestamp = datetime.now(UTC).isoformat()
    normalized_status = normalize_plan_status(status)
    if normalized_status == "approved":
        normalized_status = "awaiting_approval"
    revisions = list((existing or {}).get("revisions") or [])
    revisions.append(
        {
            "revision_number": revision_count,
            "source": source,
            "note": note or summary,
            "status": normalized_status,
            "updated_at": timestamp,
        }
    )
    return {
        "summary": summary.strip(),
        "phases": normalize_plan_items(phases),
        "deliverables": normalize_plan_items(deliverables),
        "open_questions": normalize_plan_items(open_questions),
        "acceptance_criteria": normalize_plan_items(acceptance_criteria),
        "risk_points": normalize_plan_items(risk_points),
        "revision_count": revision_count,
        "status": normalized_status,
        "updated_at": timestamp,
        "revisions": revisions,
    }
