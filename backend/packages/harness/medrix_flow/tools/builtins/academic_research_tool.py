from __future__ import annotations

from pathlib import Path
from typing import Annotated

from langchain.tools import InjectedToolCallId, ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.typing import ContextT

from medrix_flow.academic import AcademicRepository, AcademicResearchService
from medrix_flow.agents.thread_state import ThreadState
from medrix_flow.config.paths import VIRTUAL_PATH_PREFIX, get_paths
from medrix_flow.runtime.db import SQLiteRuntimeDB


@tool("academic_research", parse_docstring=True)
async def academic_research_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    topic: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    scope: str | None = None,
    include_graph: bool = False,
    max_candidates: int = 120,
    core_paper_limit: int = 24,
) -> Command:
    """Run the academic literature pipeline and produce report artifacts.

    Use this tool when the user asks for a literature review, experiment report,
    academic report, APA references, innovation-point mining, or a research
    evidence pack from a topic.

    The tool will:
    - create or reuse a thread-scoped academic project
    - retrieve and normalize scholarly metadata
    - rank and deduplicate papers
    - synthesize a report, APA references, BibTeX, and evidence map
    - present the generated files back to the user as artifacts

    Args:
        topic: Research topic to investigate.
        scope: Optional scope, domain constraint, or audience qualifier.
        include_graph: Whether to also export graph.json.
        max_candidates: Maximum number of raw candidate records to fetch.
        core_paper_limit: Maximum number of core papers kept after ranking.
    """
    thread_id = runtime.context.get("thread_id")
    if not thread_id:
        return Command(
            update={"messages": [ToolMessage("Error: thread_id is required for academic_research.", tool_call_id=tool_call_id)]}
        )

    thread_data = runtime.state.get("thread_data") or {}
    outputs_path = thread_data.get("outputs_path")
    if not outputs_path:
        return Command(
            update={"messages": [ToolMessage("Error: thread outputs path is not available.", tool_call_id=tool_call_id)]}
        )

    db = SQLiteRuntimeDB(get_paths().academic_db_file)
    await db.connect()
    try:
        repository = AcademicRepository(db)
        await repository.setup()
        service = AcademicResearchService(repository)
        result = await service.run_research(
            thread_id=thread_id,
            topic=topic,
            scope=scope,
            output_dir=Path(outputs_path),
            include_graph=include_graph,
            max_candidates=max_candidates,
            core_paper_limit=core_paper_limit,
        )
    except Exception as exc:
        await db.close()
        return Command(
            update={"messages": [ToolMessage(f"Error: {exc}", tool_call_id=tool_call_id)]}
        )

    try:
        artifact_paths = []
        outputs_dir = Path(outputs_path).resolve()
        for filepath in result.export_files:
            relative = Path(filepath).resolve().relative_to(outputs_dir)
            artifact_paths.append(f"{VIRTUAL_PATH_PREFIX}/outputs/{relative.as_posix()}")
        included_refs = len([entry for entry in result.references if entry.included_in_final])
        summary = (
            f"Academic project `{result.project.project_id}` ready. "
            f"Core papers: {len(result.evidence_cards)} evidence cards, "
            f"APA references: {included_refs}. "
            f"Artifacts: {', '.join(Path(path).name for path in result.export_files)}"
        )
        return Command(
            update={
                "artifacts": artifact_paths,
                "messages": [ToolMessage(summary, tool_call_id=tool_call_id)],
            }
        )
    finally:
        await db.close()
