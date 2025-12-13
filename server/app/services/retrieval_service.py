from langchain_chroma import Chroma
from langchain_core.retrievers import BaseRetriever
from typing import Dict, List, Any, Optional
from app.config.settings import settings


def get_hybrid_retriever(
    vector_store: Chroma, query_intent: Dict[str, Any]
) -> BaseRetriever:
    """
    Creates and returns a retriever with a dynamic metadata filter.
    Handles multiple filter conditions by using boolean flags and logical operators.

    Args:
        vector_store: The Chroma vector store instance
        query_intent: Dictionary containing extracted query intent with keys like
                     'technologies', 'domain', etc.

    Returns:
        A configured BaseRetriever instance with metadata filters applied
    """
    filter_conditions: List[Dict[str, Any]] = []

    # Filter by technologies using boolean flags
    # Example: If technologies are ['kafka', 'sqs'], this will create
    # {'tech_kafka': {'$eq': True}} and {'tech_sqs': {'$eq': True}}
    if query_intent.get("technologies"):
        technologies: List[str] = query_intent["technologies"]
        for tech in technologies:
            filter_conditions.append({f"tech_{tech.lower()}": {"$eq": True}})

    # Filter by domain (if provided)
    if query_intent.get("domain"):
        domain: str = query_intent["domain"]
        filter_conditions.append({"domain": {"$eq": domain}})

    # Combine all conditions with a logical $and
    # This is critical for robustly filtering by multiple criteria (e.g., tech AND domain)
    combined_filter: Optional[Dict[str, Any]] = None
    if len(filter_conditions) > 1:
        # The "$and" operator requires a list with two or more conditions
        combined_filter = {"$and": filter_conditions}
    elif len(filter_conditions) == 1:
        # If there's only one condition, it can be passed directly
        combined_filter = filter_conditions[0]

    # Otherwise, combined_filter remains None, meaning no filters are applied.

    # Create the retriever with the dynamic filter
    retriever = vector_store.as_retriever(
        search_type=settings.RETRIEVAL_SEARCH_TYPE,
        search_kwargs={
            "k": settings.RETRIEVAL_K,
            "filter": combined_filter if combined_filter else None,
        },
    )

    return retriever
