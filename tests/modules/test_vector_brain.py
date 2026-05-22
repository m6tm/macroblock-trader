"""Tests Phase 8 — Cerveau Vectoriel."""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict

import numpy as np

from modules.vector_brain import (
    AdjustmentResult,
    FeatureEmbeddingEngine,
    NumpyVectorStore,
    SimilarTradeAnalysis,
    VectorDbMode,
    VectorRecord,
    analyze_similar_trades,
    best_and_worst_setups,
    build_trade_text,
    calculate_adjustment,
    create_embedding_engine,
    create_vector_store,
    find_similar_trades,
    generate_weekly_insights,
    get_vector_db_mode,
    update_trade_vector_metadata,
    vectorize_trade,
    weekly_clustering,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_trade(overrides: Dict[str, Any]) -> Dict[str, Any]:
    defaults = {
        "trade_id": "T-001",
        "signal_id": "SIG-001",
        "direction": "LONG",
        "grade": "A+",
        "setup_type": "OB+FVG",
        "killzone": "LONDON_FIX_PM",
        "macro_score": 2,
        "technical_score": 5.0,
        "score_total": 4.2,
        "rr_expected": 2.0,
        "status_virtual": "CLOSED_WIN",
        "pnl_virtual_dollars": 50.0,
        "pnl_real_dollars": 48.0,
        "user_executed": True,
        "user_feedback_status": "SUBMITTED",
        "created_at": "2026-05-20T14:00:00Z",
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# 8.1 Store
# ---------------------------------------------------------------------------
def test_numpy_vector_store_crud():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        store = NumpyVectorStore(persist_path=path)
        vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        rec = VectorRecord(trade_id="T-001", vector=vec, metadata={"grade": "A+"})
        store.add(rec)
        assert store.count() == 1

        fetched = store.get("T-001")
        assert fetched is not None
        assert fetched.trade_id == "T-001"
        np.testing.assert_array_almost_equal(fetched.vector, vec)

        # Update metadata
        assert store.update_metadata("T-001", {"grade": "B"})
        fetched2 = store.get("T-001")
        assert fetched2.metadata["grade"] == "B"

        # Delete
        assert store.delete("T-001")
        assert store.count() == 0
        assert store.get("T-001") is None
    finally:
        os.unlink(path)


def test_numpy_vector_store_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        store1 = NumpyVectorStore(persist_path=path)
        store1.add(VectorRecord(trade_id="T-001", vector=np.array([0.5, 0.5]), metadata={"a": 1}))
        store1.persist()

        store2 = NumpyVectorStore(persist_path=path)
        assert store2.count() == 1
        assert store2.get("T-001").metadata["a"] == 1
    finally:
        os.unlink(path)


def test_numpy_query_knn():
    store = NumpyVectorStore(persist_path=None)
    store.add(VectorRecord(trade_id="T-A", vector=np.array([1.0, 0.0, 0.0]), metadata={"grade": "A+"}))
    store.add(VectorRecord(trade_id="T-B", vector=np.array([0.9, 0.1, 0.0]), metadata={"grade": "B"}))
    store.add(VectorRecord(trade_id="T-C", vector=np.array([0.0, 1.0, 0.0]), metadata={"grade": "A+"}))

    results = store.query(vector=np.array([1.0, 0.0, 0.0]), n_results=2)
    assert len(results) == 2
    assert results[0].trade_id == "T-A"
    assert results[0].similarity > 0.99
    assert results[1].trade_id == "T-B"


def test_numpy_query_with_filter():
    store = NumpyVectorStore(persist_path=None)
    store.add(VectorRecord(trade_id="T-1", vector=np.array([1.0, 0.0]), metadata={"grade": "A+", "user_executed": True}))
    store.add(VectorRecord(trade_id="T-2", vector=np.array([0.99, 0.01]), metadata={"grade": "B", "user_executed": False}))

    results = store.query(
        vector=np.array([1.0, 0.0]),
        n_results=5,
        filters={"user_executed": True},
    )
    assert len(results) == 1
    assert results[0].trade_id == "T-1"


def test_create_vector_store_factory():
    # On Termux without ChromaDB installed, factory must return NumpyVectorStore
    store = create_vector_store(persist_dir="./data/chroma_db/")
    assert isinstance(store, NumpyVectorStore)


# ---------------------------------------------------------------------------
# 8.2 Embedding
# ---------------------------------------------------------------------------
def test_feature_embedding_engine():
    engine = FeatureEmbeddingEngine()
    trade = {
        "direction": "LONG",
        "grade": "A+",
        "macro_score": 2,
        "technical_score": 5.0,
        "score_total": 4.2,
        "rr_expected": 2.5,
        "setup_type": "OB+FVG",
        "killzone": "LONDON_FIX_PM",
        "sentiment_score": 1,
        "xauusd_price": 2345.0,
    }
    vec = engine.encode_trade(trade)
    assert vec.dtype == np.float32
    assert len(vec) == engine.dim
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-4  # L2 normalised


def test_feature_embedding_direction_discrimination():
    engine = FeatureEmbeddingEngine()
    long_vec = engine.encode_trade({"direction": "LONG", "grade": "A+", "setup_type": "OB"})
    short_vec = engine.encode_trade({"direction": "SHORT", "grade": "A+", "setup_type": "OB"})
    # Cosine similarity should be < 1 because direction differs
    sim = np.dot(long_vec, short_vec)
    assert sim < 0.99


def test_create_embedding_engine_fallback():
    engine = create_embedding_engine(use_st_if_available=False)
    assert isinstance(engine, FeatureEmbeddingEngine)


# ---------------------------------------------------------------------------
# 8.3 Vectorizer
# ---------------------------------------------------------------------------
def test_build_trade_text():
    text = build_trade_text({
        "direction": "LONG",
        "grade": "A+",
        "setup_type": "OB+FVG",
        "killzone": "LONDON_FIX_PM",
        "macro_score": 2,
        "technical_score": 5.0,
        "score_total": 4.2,
        "rr_expected": 2.0,
        "entry_price_actual": 2345.50,
        "sl_price": 2341.00,
        "tp1_price": 2352.00,
    })
    assert "LONG" in text
    assert "OB+FVG" in text
    assert "2345.50" in text


def test_vectorize_and_retrieve():
    store = NumpyVectorStore(persist_path=None)
    engine = FeatureEmbeddingEngine()

    trade = _make_trade({"trade_id": "VT-001", "setup_type": "OB+FVG", "pnl_virtual_dollars": 100.0})
    rec = vectorize_trade(store, engine, trade)
    assert rec is not None
    assert store.count() == 1

    # Retrieve similar
    query_trade = _make_trade({"trade_id": "Q-001", "setup_type": "OB+FVG"})
    query_vec = engine.encode_trade(query_trade)
    results = find_similar_trades(store, query_vec, n=5)
    assert len(results) == 1
    assert results[0].trade_id == "VT-001"


def test_update_trade_vector_metadata():
    store = NumpyVectorStore(persist_path=None)
    engine = FeatureEmbeddingEngine()
    trade = _make_trade({"trade_id": "UT-001"})
    vectorize_trade(store, engine, trade)

    ok = update_trade_vector_metadata(store, "UT-001", {"pnl_real_dollars": 55.0, "user_feedback_status": "SUBMITTED"})
    assert ok
    fetched = store.get("UT-001")
    assert fetched.metadata["pnl_real_dollars"] == 55.0


# ---------------------------------------------------------------------------
# 8.4 Retrieval & Analysis
# ---------------------------------------------------------------------------
def test_find_similar_trades_filter():
    store = NumpyVectorStore(persist_path=None)
    engine = FeatureEmbeddingEngine()

    t1 = _make_trade({"trade_id": "F-001", "user_executed": True, "user_feedback_status": "SUBMITTED"})
    t2 = _make_trade({"trade_id": "F-002", "user_executed": False, "user_feedback_status": None})
    vectorize_trade(store, engine, t1)
    vectorize_trade(store, engine, t2)

    q = engine.encode_trade(_make_trade({"trade_id": "FQ"}))
    results = find_similar_trades(store, q, n=5)
    assert len(results) == 1
    assert results[0].trade_id == "F-001"


def test_analyze_similar_trades():
    results = [
        type("R", (), {"trade_id": "A", "similarity": 0.95, "metadata": {"status_virtual": "CLOSED_WIN", "pnl_virtual_dollars": 10.0, "pnl_real_dollars": 9.0}})(),
        type("R", (), {"trade_id": "B", "similarity": 0.90, "metadata": {"status_virtual": "CLOSED_WIN", "pnl_virtual_dollars": 20.0, "pnl_real_dollars": 18.0}})(),
        type("R", (), {"trade_id": "C", "similarity": 0.85, "metadata": {"status_virtual": "CLOSED_LOSS", "pnl_virtual_dollars": -5.0, "pnl_real_dollars": -6.0}})(),
    ]
    analysis = analyze_similar_trades(results)
    assert analysis.win_rate == 2 / 3
    assert analysis.avg_pnl_virtual == (10 + 20 - 5) / 3
    assert analysis.avg_pnl_real == (9 + 18 - 6) / 3
    assert analysis.avg_similarity == (0.95 + 0.90 + 0.85) / 3
    assert analysis.win_count == 2
    assert analysis.loss_count == 1


def test_analyze_similar_trades_empty():
    analysis = analyze_similar_trades([])
    assert analysis.win_rate == 0.0
    assert analysis.avg_pnl_virtual == 0.0
    assert analysis.trade_ids == []


# ---------------------------------------------------------------------------
# 8.5 Adjustment
# ---------------------------------------------------------------------------
def test_get_vector_db_mode():
    assert get_vector_db_mode(10) == VectorDbMode.PASSIVE
    assert get_vector_db_mode(30) == VectorDbMode.LIGHT
    assert get_vector_db_mode(100) == VectorDbMode.LIGHT
    assert get_vector_db_mode(101) == VectorDbMode.FULL


def test_calculate_adjustment_passive():
    analysis = SimilarTradeAnalysis(
        trade_ids=["A"], similarities=[0.9],
        win_rate=0.9, avg_pnl_virtual=10, avg_pnl_real=10,
        avg_similarity=0.9, avg_rr_realized=2.0,
        win_count=1, loss_count=0, be_count=0,
    )
    res = calculate_adjustment(analysis, mode=VectorDbMode.PASSIVE)
    assert res.adjustment == 0.0
    assert res.mode == VectorDbMode.PASSIVE


def test_calculate_adjustment_light_positive():
    analysis = SimilarTradeAnalysis(
        trade_ids=["A", "B", "C", "D", "E"],
        similarities=[0.9, 0.9, 0.9, 0.9, 0.9],
        win_rate=0.85, avg_pnl_virtual=10, avg_pnl_real=10,
        avg_similarity=0.9, avg_rr_realized=2.0,
        win_count=4, loss_count=1, be_count=0,
    )
    res = calculate_adjustment(analysis, mode=VectorDbMode.LIGHT)
    assert res.adjustment == +0.1
    assert res.reason is not None


def test_calculate_adjustment_light_negative():
    analysis = SimilarTradeAnalysis(
        trade_ids=["A", "B", "C", "D", "E"],
        similarities=[0.9] * 5,
        win_rate=0.20, avg_pnl_virtual=-10, avg_pnl_real=-10,
        avg_similarity=0.9, avg_rr_realized=1.0,
        win_count=1, loss_count=4, be_count=0,
    )
    res = calculate_adjustment(analysis, mode=VectorDbMode.LIGHT)
    assert res.adjustment == -0.1


def test_calculate_adjustment_full_positive():
    analysis = SimilarTradeAnalysis(
        trade_ids=["A"] * 5,
        similarities=[0.9] * 5,
        win_rate=0.85, avg_pnl_virtual=10, avg_pnl_real=10,
        avg_similarity=0.9, avg_rr_realized=2.0,
        win_count=4, loss_count=1, be_count=0,
    )
    res = calculate_adjustment(analysis, mode=VectorDbMode.FULL)
    assert res.adjustment == +0.2


def test_calculate_adjustment_full_negative():
    analysis = SimilarTradeAnalysis(
        trade_ids=["A"] * 5,
        similarities=[0.9] * 5,
        win_rate=0.30, avg_pnl_virtual=-10, avg_pnl_real=-10,
        avg_similarity=0.9, avg_rr_realized=1.0,
        win_count=1, loss_count=4, be_count=0,
    )
    res = calculate_adjustment(analysis, mode=VectorDbMode.FULL)
    assert res.adjustment == -0.3


def test_calculate_adjustment_full_moderate():
    analysis = SimilarTradeAnalysis(
        trade_ids=["A"] * 5,
        similarities=[0.9] * 5,
        win_rate=0.65, avg_pnl_virtual=5, avg_pnl_real=5,
        avg_similarity=0.9, avg_rr_realized=2.0,
        win_count=3, loss_count=1, be_count=1,
    )
    res = calculate_adjustment(analysis, mode=VectorDbMode.FULL)
    assert res.adjustment == +0.1


# ---------------------------------------------------------------------------
# 8.6 Consolidation
# ---------------------------------------------------------------------------
def test_weekly_clustering_and_insights():
    store = NumpyVectorStore(persist_path=None)
    engine = FeatureEmbeddingEngine()

    trades = [
        _make_trade({"trade_id": f"W-{i:03d}", "setup_type": "OB+FVG", "killzone": "LONDON_FIX_PM",
                     "status_virtual": "CLOSED_WIN" if i < 4 else "CLOSED_LOSS",
                     "pnl_virtual_dollars": 20.0 if i < 4 else -10.0,
                     "pnl_real_dollars": 18.0 if i < 4 else -12.0})
        for i in range(6)
    ]
    for t in trades:
        vectorize_trade(store, engine, t)

    clusters = weekly_clustering(store)
    assert "setup:OB+FVG" in clusters
    assert "killzone:LONDON_FIX_PM" in clusters

    insights = generate_weekly_insights(clusters, min_trades=3)
    assert len(insights) > 0
    best, worst = best_and_worst_setups(insights)
    assert best is not None


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_numpy_vector_store_crud()
    test_numpy_vector_store_persistence()
    test_numpy_query_knn()
    test_numpy_query_with_filter()
    test_create_vector_store_factory()
    test_feature_embedding_engine()
    test_feature_embedding_direction_discrimination()
    test_create_embedding_engine_fallback()
    test_build_trade_text()
    test_vectorize_and_retrieve()
    test_update_trade_vector_metadata()
    test_find_similar_trades_filter()
    test_analyze_similar_trades()
    test_analyze_similar_trades_empty()
    test_get_vector_db_mode()
    test_calculate_adjustment_passive()
    test_calculate_adjustment_light_positive()
    test_calculate_adjustment_light_negative()
    test_calculate_adjustment_full_positive()
    test_calculate_adjustment_full_negative()
    test_calculate_adjustment_full_moderate()
    test_weekly_clustering_and_insights()
    print("[OK] Tous les tests Phase 8 (Cerveau Vectoriel) ont passe.")
