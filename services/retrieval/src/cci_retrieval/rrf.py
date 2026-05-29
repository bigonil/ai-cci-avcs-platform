"""Reciprocal Rank Fusion (RRF) score combiner.

Standard formula: score(d) = sum_i 1 / (k + rank_i(d))
Default k=60 (Cormack et al. 2009).
"""
from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def reciprocal_rank_fusion(
    ranked_lists: list[list[T]],
    k: int = 60,
) -> list[tuple[T, float]]:
    """Merge N ranked lists into a single list sorted by descending RRF score.

    Each element of ranked_lists is an ordered list of document IDs (rank 0 = best).
    Returns list of (doc_id, rrf_score) sorted descending.
    """
    scores: dict[T, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def fuse_search_results(
    dense_hits: list[dict],
    bm25_hits: list[dict],
    id_key: str = "chunk_id",
    k: int = 60,
) -> list[dict]:
    """Fuse dense and BM25 search result dicts using RRF.

    Preserves full payload from the source that found the document.
    Dense hits take precedence for payload when both sources match.
    Returns merged list sorted by descending RRF score.
    """
    payloads: dict[str, dict] = {}
    for hit in bm25_hits:
        cid = hit.get(id_key) or hit.get("payload", {}).get(id_key, "")
        if cid:
            payloads[cid] = hit

    for hit in dense_hits:
        cid = hit.get(id_key) or hit.get("payload", {}).get(id_key, "")
        if cid:
            payloads[cid] = hit

    dense_order = [
        h.get(id_key) or h.get("payload", {}).get(id_key, "") for h in dense_hits
    ]
    bm25_order = [
        h.get(id_key) or h.get("payload", {}).get(id_key, "") for h in bm25_hits
    ]

    fused = reciprocal_rank_fusion([dense_order, bm25_order], k=k)
    result = []
    for doc_id, rrf_score in fused:
        if doc_id and doc_id in payloads:
            entry = dict(payloads[doc_id])
            entry["rrf_score"] = rrf_score
            result.append(entry)
    return result
