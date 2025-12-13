"""
Retrieval service that provides true hybrid search capabilities.
Combines vector similarity, BM25 keyword search, and metadata filtering.
"""
from langchain_chroma import Chroma
from langchain_core.retrievers import BaseRetriever
from typing import Dict, List, Any, Optional
from app.config.settings import settings
from app.services.hybrid_retriever import HybridRetriever
from app.services.query_classifier import QueryClassifier


def get_hybrid_retriever(
    vector_store: Chroma, query_intent: Dict[str, Any], query: Optional[str] = None
) -> BaseRetriever:
    """
    Creates and returns a true hybrid retriever that combines:
    - Vector similarity search (semantic)
    - BM25 keyword search (sparse)
    - Metadata filtering
    - Reciprocal Rank Fusion (RRF) for result merging

    Args:
        vector_store: The Chroma vector store instance
        query_intent: Dictionary containing extracted query intent with keys like
                     'technologies', 'domain', 'author', 'status', 'date_from', 'date_to', etc.
        query: Optional query string for query type classification

    Returns:
        A HybridRetriever instance configured for the query
    """
    # Classify query type if not already set
    if not query_intent.get("query_type") and query:
        classifier = QueryClassifier()
        query_type = classifier.classify_query(query)
        query_intent["query_type"] = query_type

    # Use true hybrid search if enabled, otherwise fall back to simple vector search
    if settings.HYBRID_SEARCH_ENABLED:
        return HybridRetriever(vector_store=vector_store, query_intent=query_intent)
    else:
        # Fallback to simple vector search with metadata filters (legacy behavior)
        return _get_simple_retriever(vector_store, query_intent)


def _get_simple_retriever(
    vector_store: Chroma, query_intent: Dict[str, Any]
) -> BaseRetriever:
    """
    Legacy simple retriever with metadata filtering only.
    Used when hybrid search is disabled.
    """
    filter_conditions: List[Dict[str, Any]] = []

    # Filter by technologies using boolean flags
    if query_intent.get("technologies"):
        technologies: List[str] = query_intent["technologies"]
        for tech in technologies:
            filter_conditions.append({f"tech_{tech.lower()}": {"$eq": True}})

    # Filter by domain (if provided)
    if query_intent.get("domain"):
        domain: str = query_intent["domain"]
        filter_conditions.append({"domain": {"$eq": domain}})

    # Combine all conditions with a logical $and
    combined_filter: Optional[Dict[str, Any]] = None
    if len(filter_conditions) > 1:
        combined_filter = {"$and": filter_conditions}
    elif len(filter_conditions) == 1:
        combined_filter = filter_conditions[0]

    # Create the retriever with the dynamic filter
    retriever = vector_store.as_retriever(
        search_type=settings.RETRIEVAL_SEARCH_TYPE,
        search_kwargs={
            "k": settings.RETRIEVAL_K,
            "filter": combined_filter if combined_filter else None,
        },
    )

    return retriever
