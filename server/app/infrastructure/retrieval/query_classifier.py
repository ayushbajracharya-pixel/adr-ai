"""
Query classification service to determine the appropriate search strategy.
Classifies queries into: list, filter, semantic, or hybrid search types.
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, Any, Optional
import re

from app.core.config import settings


class QueryClassifier:
    """Classifies user queries to determine the best search strategy."""

    def __init__(self) -> None:
        """Initialize the query classifier."""
        self.llm = ChatOpenAI(
            model=settings.EXTRACTION_MODEL_NAME,
            temperature=settings.EXTRACTION_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.classification_chain = self._build_classification_chain()

    def classify_query(self, query: str) -> str:
        """
        Classify a query to determine search type.

        Args:
            query: The user's query

        Returns:
            Query type: 'list', 'filter', 'semantic', or 'hybrid'
        """
        query_lower = query.lower().strip()

        # Quick heuristic checks for list queries
        list_patterns = [
            r"what (projects|adrs|decisions) (have|do) (we|you|i)",
            r"list (all|all the|some|the) (projects|adrs|decisions)",
            r"show (me )?(all|all the|some|the) (projects|adrs|decisions)",
            r"what (are|is) (all|all the|some|the) (projects|adrs|decisions)",
            r"get (all|all the|some|the) (projects|adrs|decisions)",
        ]

        for pattern in list_patterns:
            if re.search(pattern, query_lower):
                return "list"

        # Check for metadata-only filter queries
        filter_indicators = [
            r"where (author|status|date|domain)",
            r"by (author|status|date|domain)",
            r"author (is|equals|==|:|\s+['\"])",
            r"status (is|equals|==|:|\s+['\"])",
            r"accepted (adrs|projects|decisions)",
            r"proposed (adrs|projects|decisions)",
            r"superseded (adrs|projects|decisions)",
        ]

        has_metadata_filter = any(re.search(pattern, query_lower) for pattern in filter_indicators)
        has_semantic_content = len(query.split()) > 3  # More than just filter keywords

        if has_metadata_filter and not has_semantic_content:
            return "filter"

        # Use LLM for more nuanced classification
        try:
            classification = self.classification_chain.invoke({"query": query}).strip().lower()
            
            if "list" in classification:
                return "list"
            elif "filter" in classification:
                return "filter"
            elif "semantic" in classification:
                return "semantic"
            else:
                return "hybrid"  # Default to hybrid
        except Exception as e:
            print(f"Query classification failed: {e}. Defaulting to hybrid search.")
            return "hybrid"

    def _build_classification_chain(self):
        """Build the LLM-based classification chain."""
        prompt = ChatPromptTemplate.from_template(
            """
            Classify the following user query into one of these categories:
            - "list": User wants to list/enumerate ADRs (e.g., "What ADRs do we have?", "List all accepted ADRs")
            - "filter": User wants to filter ADRs by metadata only without semantic search (e.g., "ADRs by author X", "Show accepted ADRs")
            - "semantic": User wants semantic search but no specific metadata filters (e.g., "How do we handle authentication?")
            - "hybrid": User wants both semantic search and metadata filtering (e.g., "Have you considered kafka in past projects in 2024")

            Query: {query}

            Respond with ONLY one word: list, filter, semantic, or hybrid
            """
        )

        return prompt | self.llm | StrOutputParser()

