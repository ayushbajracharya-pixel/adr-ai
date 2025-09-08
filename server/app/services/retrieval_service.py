from langchain_chroma import Chroma
from typing import Dict


def get_hybrid_retriever(vector_store: Chroma, query_intent: Dict):
    """
    Creates and returns a retriever with a dynamic metadata filter.
    Handles multiple filter conditions by using boolean flags and logical operators.
    """
    filter_conditions = []

    # Filter by technologies using boolean flags
    # Example: If technologies are ['kafka', 'sqs'], this will create
    # {'tech_kafka': {'$eq': True}} and {'tech_sqs': {'$eq': True}}
    if query_intent.get("technologies"):
        for tech in query_intent["technologies"]:
            filter_conditions.append({f"tech_{tech.lower()}": {"$eq": True}})

    # Filter by domain (if provided)
    if query_intent.get("domain"):
        filter_conditions.append({"domain": {"$eq": query_intent["domain"]}})

    # Combine all conditions with a logical $and
    # This is critical for robustly filtering by multiple criteria (e.g., tech AND domain)
    combined_filter = {}
    if len(filter_conditions) > 1:
        # The "$and" operator requires a list with two or more conditions
        combined_filter = {"$and": filter_conditions}
    elif len(filter_conditions) == 1:
        # If there's only one condition, it can be passed directly
        combined_filter = filter_conditions[0]

    # Otherwise, combined_filter remains an empty dictionary, meaning no filters are applied.

    # Create the retriever with the dynamic filter
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 5,
            "filter": combined_filter if combined_filter else None,
        },
    )

    return retriever
