"""Cerveau Vectoriel — vector memory & learning module."""

from modules.vector_brain.adjustment import (
    AdjustmentResult,
    VectorDbMode,
    calculate_adjustment,
    get_vector_db_mode,
)
from modules.vector_brain.consolidation import (
    WeeklyInsight,
    best_and_worst_setups,
    generate_weekly_insights,
    weekly_clustering,
)
from modules.vector_brain.embedding import (
    EmbeddingEngine,
    FeatureEmbeddingEngine,
    create_embedding_engine,
)
from modules.vector_brain.retrieval import (
    SimilarTradeAnalysis,
    analyze_similar_trades,
    find_similar_trades,
)
from modules.vector_brain.store import (
    ChromaVectorStore,
    NumpyVectorStore,
    RetrievalResult,
    VectorRecord,
    VectorStore,
    create_vector_store,
)
from modules.vector_brain.vectorizer import (
    build_trade_text,
    update_trade_vector_metadata,
    vectorize_trade,
)

__all__ = [
    # Store
    "VectorStore",
    "VectorRecord",
    "RetrievalResult",
    "NumpyVectorStore",
    "ChromaVectorStore",
    "create_vector_store",
    # Embedding
    "EmbeddingEngine",
    "FeatureEmbeddingEngine",
    "create_embedding_engine",
    # Retrieval
    "SimilarTradeAnalysis",
    "find_similar_trades",
    "analyze_similar_trades",
    # Adjustment
    "AdjustmentResult",
    "VectorDbMode",
    "get_vector_db_mode",
    "calculate_adjustment",
    # Vectorizer
    "vectorize_trade",
    "update_trade_vector_metadata",
    "build_trade_text",
    # Consolidation
    "WeeklyInsight",
    "weekly_clustering",
    "generate_weekly_insights",
    "best_and_worst_setups",
]
