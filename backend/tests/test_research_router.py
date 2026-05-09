from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.routers import research
from medrix_flow.research import ResearchQuestService, ResearchRepository
from medrix_flow.runtime.db import SQLiteRuntimeDB


def test_research_router_end_to_end():
    async def make_service() -> tuple[ResearchQuestService, SQLiteRuntimeDB]:
        db = SQLiteRuntimeDB(":memory:")
        await db.connect()
        repo = ResearchRepository(db)
        await repo.setup()
        return ResearchQuestService(repo), db

    service, db = asyncio.run(make_service())
    app = FastAPI()
    app.state.research_service = service
    app.include_router(research.router)

    with TestClient(app) as client:
        created = client.post(
            "/api/research/quests",
            json={
                "thread_id": "thread-router-research",
                "topic": "research assistant evidence gates",
                "objective": "Track evidence and reviewer gates",
            },
        )
        assert created.status_code == 200
        quest_id = created.json()["quest"]["quest_id"]

        listed = client.get("/api/research/quests?thread_id=thread-router-research")
        assert listed.status_code == 200
        assert listed.json()["data"][0]["quest_id"] == quest_id

        advanced = client.post(
            f"/api/research/quests/{quest_id}/advance",
            json={
                "inputs": {
                    "claims": [
                        {
                            "claim": "Evidence gates improve citation integrity.",
                            "support_status": "supported",
                            "confidence": 0.7,
                        }
                    ]
                }
            },
        )
        assert advanced.status_code == 200
        assert advanced.json()["quest"]["stage"] == "literature"

        snapshot = client.get(f"/api/research/quests/{quest_id}")
        assert snapshot.status_code == 200
        assert snapshot.json()["quest"]["quest_id"] == quest_id
        assert len(snapshot.json()["evidence"]) == 1
        assert len(snapshot.json()["ledger"]) >= 2

        evidence = client.get(f"/api/research/quests/{quest_id}/evidence")
        assert evidence.status_code == 200
        assert evidence.json()["data"][0]["support_status"] == "supported"

        invalid = client.post(
            f"/api/research/quests/{quest_id}/advance",
            json={"target_stage": "experiment_planned"},
        )
        assert invalid.status_code == 422

    asyncio.run(db.close())
