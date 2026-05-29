"""Unit tests for Reciprocal Rank Fusion."""
from __future__ import annotations

from cci_retrieval.rrf import fuse_search_results, reciprocal_rank_fusion


class TestReciprocalRankFusion:
    def test_single_list(self) -> None:
        ranked = [["a", "b", "c"]]
        result = reciprocal_rank_fusion(ranked, k=60)
        ids = [r[0] for r in result]
        assert ids == ["a", "b", "c"]

    def test_two_lists_same_order(self) -> None:
        result = reciprocal_rank_fusion([["a", "b"], ["a", "b"]], k=60)
        # 'a' should have higher score than 'b' — both lists agree
        assert result[0][0] == "a"
        assert result[0][1] > result[1][1]

    def test_two_lists_reversed(self) -> None:
        # Dense: [a, b, c]  BM25: [c, b, a]
        # RRF math: score(a) = 1/61 + 1/63 ≈ 0.032266 (rank 0 + rank 2)
        #           score(b) = 1/62 + 1/62 ≈ 0.032258 (rank 1 + rank 1)
        #           score(c) = 1/63 + 1/61 ≈ 0.032266 (rank 2 + rank 0)
        # a and c are symmetric (equal); b scores slightly less (never tops either list)
        result = reciprocal_rank_fusion([["a", "b", "c"], ["c", "b", "a"]], k=60)
        scores = dict(result)
        assert abs(scores["a"] - scores["c"]) < 1e-10  # symmetric
        assert scores["a"] > scores["b"]               # top-ranker beats consistent-middle

    def test_empty_lists(self) -> None:
        assert reciprocal_rank_fusion([]) == []
        assert reciprocal_rank_fusion([[]], k=60) == []

    def test_unique_items_from_one_list(self) -> None:
        result = reciprocal_rank_fusion([["a"], ["b"]], k=60)
        ids = {r[0] for r in result}
        assert ids == {"a", "b"}

    def test_k_parameter_affects_scores(self) -> None:
        result_k1 = reciprocal_rank_fusion([["a", "b"]], k=1)
        result_k100 = reciprocal_rank_fusion([["a", "b"]], k=100)
        # With lower k, rank differences have more impact
        ratio_k1 = result_k1[0][1] / result_k1[1][1]
        ratio_k100 = result_k100[0][1] / result_k100[1][1]
        assert ratio_k1 > ratio_k100


class TestFuseSearchResults:
    def test_fuse_merges_both_sources(self, sample_chunks: list[dict]) -> None:
        dense = sample_chunks[:3]
        bm25 = sample_chunks[1:]
        fused = fuse_search_results(dense, bm25, id_key="chunk_id")
        ids = {r["chunk_id"] for r in fused}
        assert "chunk-001" in ids
        assert "chunk-004" in ids

    def test_fused_has_rrf_score(self, sample_chunks: list[dict]) -> None:
        fused = fuse_search_results(sample_chunks[:2], sample_chunks[1:3], id_key="chunk_id")
        assert all("rrf_score" in r for r in fused)

    def test_dense_payload_takes_precedence(self, sample_chunks: list[dict]) -> None:
        dense = [{"chunk_id": "c1", "text": "from dense", "_dense_score": 0.9}]
        bm25 = [{"chunk_id": "c1", "text": "from bm25", "bm25_score": 0.5}]
        fused = fuse_search_results(dense, bm25, id_key="chunk_id")
        assert fused[0]["text"] == "from dense"

    def test_empty_inputs(self) -> None:
        assert fuse_search_results([], [], id_key="chunk_id") == []
        result = fuse_search_results([{"chunk_id": "a", "text": "x"}], [], id_key="chunk_id")
        assert result[0]["chunk_id"] == "a"
