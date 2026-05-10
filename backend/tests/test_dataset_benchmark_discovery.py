from __future__ import annotations

import asyncio
import json

import httpx

from medrix_flow.benchmarks import DatasetBenchmarkDiscoveryService
from medrix_flow.tools.tools import get_available_tools


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def test_dataset_benchmark_discovery_schema_and_source_normalization(tmp_path, monkeypatch):
    async def fake_get(self, url: str):
        if "huggingface.co/api/datasets" in url:
            return FakeResponse(
                [
                    {
                        "id": "org/medical-benchmark",
                        "lastModified": "2026-01-02T00:00:00Z",
                        "tags": ["task_categories:classification", "modality:tabular", "license:cc-by-4.0", "f1"],
                    }
                ]
            )
        if "openml.org/api" in url:
            return FakeResponse({"data": {"dataset": [{"did": "61", "name": "medical benchmark", "licence": "Public"}]}})
        raise AssertionError(url)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    service = DatasetBenchmarkDiscoveryService()

    benchmark_map, path = asyncio.run(
        service.discover(
            topic="medical benchmark classification",
            scope="tabular",
            output_dir=tmp_path,
            sources=["hf", "openml"],
        )
    )

    assert path.name == "dataset_benchmark_map.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert benchmark_map.sources_requested == ["huggingface", "openml"]
    assert payload["entries"][0]["name"] == "org/medical-benchmark"
    assert payload["entries"][0]["license"] == "cc-by-4.0"
    assert payload["entries"][0]["metrics"] == ["f1"]
    assert payload["entries"][0]["download_feasibility"] == "check_dataset_card_and_gating"


def test_dataset_benchmark_tool_is_registered(monkeypatch):
    monkeypatch.setattr("medrix_flow.tools.tools.get_app_config", lambda: type("Config", (), {"tools": [], "models": [], "tool_search": type("ToolSearch", (), {"enabled": False})()})())
    names = {tool.name for tool in get_available_tools(include_mcp=False)}
    assert "dataset_benchmark_discovery" in names
