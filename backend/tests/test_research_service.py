from __future__ import annotations

import asyncio

import pytest

from medrix_flow.research import ResearchQuestService, ResearchRepository
from medrix_flow.runtime.db import SQLiteRuntimeDB


async def _make_service() -> tuple[ResearchQuestService, SQLiteRuntimeDB]:
    db = SQLiteRuntimeDB(":memory:")
    await db.connect()
    repo = ResearchRepository(db)
    await repo.setup()
    return ResearchQuestService(repo), db


async def _advance_to_results_stage(service: ResearchQuestService, quest_id: str) -> None:
    await service.advance_quest(quest_id)
    await service.advance_quest(quest_id, inputs={"overlap_risk": "low"})
    await service.advance_quest(quest_id)
    await service.advance_quest(quest_id)
    await service.decide_gate(
        quest_id,
        stage="experiment_running",
        gate_type="experiment_execution",
        status="approved",
    )
    await service.advance_quest(quest_id, inputs={"experiment_project_id": "exp-manuscript-test"})
    await service.advance_quest(quest_id, inputs={"metrics": {"accuracy": 0.82}})


def test_research_quest_lifecycle_gates_and_artifacts():
    async def scenario() -> None:
        service, db = await _make_service()
        quest = await service.create_quest(
            thread_id="thread-research-1",
            topic="claim-level evidence checking for biomedical agents",
            objective="Build a verifiable research assistant workflow",
        )
        assert quest.stage == "intake"

        literature = await service.advance_quest(
            quest.quest_id,
            inputs={
                "academic_project_id": "academic-1",
                "claims": [
                    {
                        "claim": "Claim-level citation checks reduce unsupported manuscript claims.",
                        "source_title": "Evidence Checking Systems",
                        "locator": "p. 3",
                        "snippet": "Citation checks identify unsupported claims in generated manuscripts.",
                        "support_status": "supported",
                        "confidence": 0.8,
                    }
                ],
            },
        )
        assert literature.quest.stage == "literature"
        assert literature.generated["claim_count"] == 1

        novelty = await service.advance_quest(
            quest.quest_id,
            inputs={
                "idea": "Claim-level evidence checking for biomedical agents",
                "closest_papers": [{"title": "Audit trails for research agents"}],
                "hypotheses": ["Evidence gates reduce unsupported claims."],
            },
        )
        assert novelty.quest.stage == "novelty_check"
        assert novelty.generated["decision"] == "proceed"

        evidence = await service.advance_quest(quest.quest_id)
        assert evidence.quest.stage == "evidence_verified"
        assert evidence.generated["support_status_counts"]["supported"] == 1

        planned = await service.advance_quest(
            quest.quest_id,
            inputs={"branches": [{"name": "Baseline evidence verifier", "branch_type": "baseline", "priority": 1.0}]},
        )
        assert planned.quest.stage == "experiment_planned"
        assert planned.generated["execution_gate"] == "experiment_execution"

        blocked_run = await service.advance_quest(quest.quest_id)
        assert blocked_run.blocked is True
        assert blocked_run.required_gate is not None
        assert blocked_run.required_gate.gate_type == "experiment_execution"

        await service.decide_gate(
            quest.quest_id,
            stage="experiment_running",
            gate_type="experiment_execution",
            status="approved",
            reason="Small local fixture only.",
        )
        running = await service.advance_quest(
            quest.quest_id,
            inputs={"experiment_project_id": "exp-1"},
            artifacts=["/mnt/user-data/outputs/metrics.json"],
        )
        assert running.quest.stage == "experiment_running"
        assert running.generated["branch_status"] == "completed"

        results = await service.advance_quest(
            quest.quest_id,
            inputs={"metrics": {"unsupported_claim_rate": 0.1}},
        )
        assert results.quest.stage == "results_synthesized"
        assert "unsupported_claim_rate" in results.generated["metric_keys"]

        manuscript = await service.advance_quest(quest.quest_id)
        assert manuscript.quest.stage == "manuscript_draft"
        assert manuscript.generated["review_gate"] == "pre_review"

        blocked_review = await service.advance_quest(quest.quest_id)
        assert blocked_review.blocked is True
        assert blocked_review.required_gate is not None
        assert blocked_review.required_gate.gate_type == "pre_review"

        await service.decide_gate(
            quest.quest_id,
            stage="review",
            gate_type="pre_review",
            status="approved",
        )
        review = await service.advance_quest(quest.quest_id)
        assert review.quest.stage == "review"
        assert review.generated["reviewer_count"] == 4

        revision = await service.advance_quest(
            quest.quest_id,
            inputs={"completed_actions": ["Documented baselines and limitations."]},
        )
        assert revision.quest.stage == "revision"

        blocked_final = await service.advance_quest(quest.quest_id)
        assert blocked_final.blocked is True
        assert blocked_final.required_gate is not None
        assert blocked_final.required_gate.gate_type == "final_release"

        await service.decide_gate(
            quest.quest_id,
            stage="final_bundle",
            gate_type="final_release",
            status="approved",
        )
        final = await service.advance_quest(quest.quest_id, artifacts=["/mnt/user-data/outputs/manuscript.md"])
        assert final.quest.stage == "final_bundle"
        assert final.quest.status == "completed"

        snapshot = await service.get_snapshot(quest.quest_id)
        assert len(snapshot.ledger) >= 10
        assert len(snapshot.evidence) == 1
        assert len(snapshot.experiment_branches) == 1
        assert len(snapshot.manuscript_sections) >= 5
        assert len(snapshot.reviewer_reports) == 4
        await db.close()

    asyncio.run(scenario())


def test_manuscript_draft_auto_fills_content():
    async def scenario() -> None:
        service, db = await _make_service()
        quest = await service.create_quest(thread_id="thread-manuscript-1", topic="citation key auditing")
        await _advance_to_results_stage(service, quest.quest_id)

        async def generator(section_key, snapshot):
            return f"Generated content for {section_key} in {snapshot.quest.title}."

        manuscript = await service.advance_quest(quest.quest_id, content_generator=generator)

        assert manuscript.quest.stage == "manuscript_draft"
        assert manuscript.generated["content_generation_errors"] == []
        sections = await service.list_manuscript_sections(quest.quest_id)
        assert len(sections) >= 5
        assert all(section.content.startswith("Generated content for ") for section in sections)
        await db.close()

    asyncio.run(scenario())


def test_manuscript_draft_generator_failure_fallback():
    async def scenario() -> None:
        service, db = await _make_service()
        quest = await service.create_quest(thread_id="thread-manuscript-2", topic="review gate resilience")
        await _advance_to_results_stage(service, quest.quest_id)

        async def generator(section_key, snapshot):
            raise RuntimeError(f"cannot generate {section_key} for {snapshot.quest.quest_id}")

        manuscript = await service.advance_quest(quest.quest_id, content_generator=generator)

        assert manuscript.quest.stage == "manuscript_draft"
        assert len(manuscript.generated["content_generation_errors"]) >= 5
        sections = await service.list_manuscript_sections(quest.quest_id)
        assert len(sections) >= 5
        assert all(section.content == "" for section in sections)
        await db.close()

    asyncio.run(scenario())


def test_results_synthesized_hypothesis_outcomes():
    async def scenario() -> None:
        service, db = await _make_service()
        quest = await service.create_quest(thread_id="thread-results-1", topic="accuracy improvements")
        await service.advance_quest(quest.quest_id)
        await service.advance_quest(
            quest.quest_id,
            inputs={
                "overlap_risk": "low",
                "hypotheses": ["The intervention improves accuracy."],
            },
        )
        await service.advance_quest(quest.quest_id)
        await service.advance_quest(
            quest.quest_id,
            inputs={
                "branches": [
                    {
                        "name": "Baseline",
                        "branch_type": "baseline",
                        "metrics": {"accuracy": 0.70},
                        "priority": 0.5,
                    },
                    {
                        "name": "Intervention",
                        "branch_type": "ablation",
                        "metrics": {"accuracy": 0.85},
                        "priority": 1.0,
                    },
                ]
            },
        )
        await service.decide_gate(
            quest.quest_id,
            stage="experiment_running",
            gate_type="experiment_execution",
            status="approved",
        )
        await service.advance_quest(quest.quest_id, inputs={"experiment_project_id": "exp-results-test"})

        results = await service.advance_quest(
            quest.quest_id,
            inputs={
                "hypotheses": [
                    {
                        "id": "hyp-accuracy",
                        "statement": "The intervention improves accuracy.",
                        "primary_metric": "accuracy",
                    }
                ],
                "metrics": {"accuracy_p_value": 0.03, "effect_ci_lower": 0.02, "effect_ci_upper": 0.14},
            },
        )

        assert results.quest.stage == "results_synthesized"
        outcomes = results.generated["hypothesis_outcomes"]
        assert outcomes[0]["hypothesis_id"] == "hyp-accuracy"
        assert outcomes[0]["outcome"] == "supported"
        assert outcomes[0]["evidence_metric_keys"] == ["accuracy"]
        assert results.generated["significance_summary"] == {
            "has_significance_data": True,
            "significant_keys": ["accuracy_p_value", "effect_ci"],
            "alpha": 0.05,
        }
        await db.close()

    asyncio.run(scenario())


def test_results_synthesized_hypothesis_outcomes_are_inconclusive_without_metrics():
    async def scenario() -> None:
        service, db = await _make_service()
        quest = await service.create_quest(thread_id="thread-results-2", topic="missing metric hypothesis")
        await service.advance_quest(quest.quest_id)
        await service.advance_quest(quest.quest_id, inputs={"overlap_risk": "low"})
        await service.advance_quest(quest.quest_id)
        await service.advance_quest(quest.quest_id)
        await service.decide_gate(
            quest.quest_id,
            stage="experiment_running",
            gate_type="experiment_execution",
            status="approved",
        )
        await service.advance_quest(quest.quest_id, inputs={"experiment_project_id": "exp-results-missing"})

        results = await service.advance_quest(
            quest.quest_id,
            inputs={
                "hypotheses": [
                    {
                        "id": "hyp-missing",
                        "statement": "The intervention improves accuracy.",
                        "primary_metric": "accuracy",
                    }
                ]
            },
        )

        assert results.generated["hypothesis_outcomes"][0]["outcome"] == "inconclusive"
        assert results.generated["significance_summary"]["has_significance_data"] is False
        await db.close()

    asyncio.run(scenario())


def test_research_quest_rejects_invalid_stage_jump():
    async def scenario() -> None:
        service, db = await _make_service()
        quest = await service.create_quest(thread_id="thread-research-2", topic="novelty gates")
        with pytest.raises(ValueError, match="Invalid research stage transition"):
            await service.advance_quest(quest.quest_id, target_stage="experiment_planned")
        await db.close()

    asyncio.run(scenario())


def test_empirical_research_quest_attaches_method_skill_and_branch_contract():
    async def scenario() -> None:
        service, db = await _make_service()
        quest = await service.create_quest(
            thread_id="thread-empirical-1",
            topic="DID evaluation of education policy effects on student outcomes",
            objective="Run an empirical public policy analysis with event-study robustness.",
        )

        assert quest.domain == "empirical_social_science"
        assert "empirical-research-methods" in quest.metadata["skill_guidance"]
        assert quest.metadata["methodology_skill_path"] == "/mnt/skills/public/empirical-research-methods/SKILL.md"
        assert {"did", "event_study"} <= set(quest.metadata["empirical_methods"])

        await service.advance_quest(quest.quest_id)
        await service.advance_quest(
            quest.quest_id,
            inputs={
                "idea": "DID evaluation of education policy effects on student outcomes",
                "closest_papers": [{"title": "Education policy and student outcomes"}],
                "overlap_risk": "low",
            },
        )
        await service.advance_quest(quest.quest_id)
        planned = await service.advance_quest(quest.quest_id)

        assert planned.quest.stage == "experiment_planned"
        snapshot = await service.get_snapshot(quest.quest_id)
        branch = snapshot.experiment_branches[0]
        assert branch.metadata["skill_guidance"] == "empirical-research-methods"
        assert branch.metadata["identification_gate"] == "required before causal claims"
        assert branch.metadata["experiment_lab_metadata_required"]["required"]
        await db.close()

    asyncio.run(scenario())


def test_high_overlap_blocks_experiment_planning_until_override():
    async def scenario() -> None:
        service, db = await _make_service()
        quest = await service.create_quest(thread_id="thread-research-3", topic="graph neural network citation verifier")
        await service.advance_quest(quest.quest_id)
        await service.advance_quest(
            quest.quest_id,
            inputs={
                "idea": "Graph neural network citation verifier",
                "closest_papers": [{"title": "Graph neural network citation verifier"}],
            },
        )
        await service.advance_quest(quest.quest_id)
        blocked = await service.advance_quest(quest.quest_id)
        assert blocked.blocked is True
        assert blocked.required_gate is not None
        assert blocked.required_gate.gate_type == "novelty_override"

        await service.decide_gate(
            quest.quest_id,
            stage="experiment_planned",
            gate_type="novelty_override",
            status="approved",
            reason="User explicitly accepts overlap risk for replication.",
        )
        planned = await service.advance_quest(quest.quest_id)
        assert planned.quest.stage == "experiment_planned"
        await db.close()

    asyncio.run(scenario())
