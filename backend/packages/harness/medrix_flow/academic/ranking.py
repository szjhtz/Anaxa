from __future__ import annotations

from collections import defaultdict

from .types import PaperRecord
from .utils import (
    citation_score,
    completeness_score,
    local_upload_bonus,
    recency_score,
    relevance_score,
)


def score_papers(papers: list[PaperRecord], *, terms: set[str]) -> list[PaperRecord]:
    scored: list[PaperRecord] = []
    for paper in papers:
        paper.relevance_score = round(relevance_score(paper, terms), 4)
        paper.recency_score = round(recency_score(paper.year), 4)
        paper.completeness_score = round(completeness_score(paper), 4)
        cite_score = citation_score(paper.cited_by_count)
        paper.rank_score = round(
            paper.relevance_score * 0.45
            + paper.completeness_score * 0.2
            + paper.recency_score * 0.15
            + cite_score * 0.15
            + local_upload_bonus(paper)
            + (0.05 if paper.provider in {"openalex", "pubmed"} else 0.0),
            4,
        )
        scored.append(paper)
    return sorted(scored, key=lambda item: item.rank_score, reverse=True)


def select_core_papers(
    papers: list[PaperRecord],
    *,
    limit: int,
) -> list[PaperRecord]:
    selected: list[PaperRecord] = []
    provider_counts: dict[str, int] = defaultdict(int)
    keyword_signatures: set[tuple[str, ...]] = set()

    for paper in papers:
        signature = tuple(sorted(paper.keywords[:4]))
        provider_cap = max(3, limit // 2)
        if provider_counts[paper.provider] >= provider_cap and paper.provider != "local-upload":
            continue
        if signature and signature in keyword_signatures and paper.rank_score < 0.75:
            continue

        selected.append(paper)
        provider_counts[paper.provider] += 1
        if signature:
            keyword_signatures.add(signature)
        if len(selected) >= limit:
            break

    if len(selected) < min(limit, len(papers)):
        seen_ids = {paper.paper_id for paper in selected}
        for paper in papers:
            if paper.paper_id in seen_ids:
                continue
            selected.append(paper)
            if len(selected) >= limit:
                break

    return selected
