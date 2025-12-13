"""
True hybrid search implementation combining vector similarity, BM25 keyword search,
and metadata filtering with Reciprocal Rank Fusion (RRF) for result merging.

Industry standard approach following best practices for hybrid retrieval.
"""
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict
import re
from rank_bm25 import BM25Okapi
from pydantic import ConfigDict
from datetime import datetime

from app.core.config import settings
from app.utils.text_processing import normalize_technology_name, normalize_domain, normalize_status


class HybridRetriever(BaseRetriever):
    """
    True hybrid retriever that combines:
    1. Dense vector search (semantic similarity)
    2. Sparse BM25 search (keyword matching)
    3. Metadata filtering
    4. Reciprocal Rank Fusion (RRF) for result merging
    """
    
    # Allow arbitrary types and extra fields
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def __init__(
        self,
        vector_store: Chroma,
        query_intent: Dict[str, Any],
        documents_cache: Optional[List[Document]] = None,
    ) -> None:
        """
        Initialize the hybrid retriever.

        Args:
            vector_store: Chroma vector store instance
            query_intent: Extracted query intent with filters and query type
            documents_cache: Optional pre-loaded documents for BM25 (for performance)
        """
        super().__init__()
        # Use __dict__ to set attributes directly, bypassing Pydantic validation
        # This is necessary because BaseRetriever is a Pydantic model
        self.__dict__["vector_store"] = vector_store
        # Ensure query_intent is a dict and has query_type set
        if not isinstance(query_intent, dict):
            query_intent = {}
        if "query_type" not in query_intent:
            query_intent["query_type"] = "hybrid"
        self.__dict__["query_intent"] = query_intent
        self.__dict__["query_type"] = query_intent.get("query_type", "hybrid")
        self.__dict__["documents_cache"] = documents_cache

    @property
    def query_type(self) -> str:
        """Get query type with safe fallback."""
        return self.__dict__.get("query_type", "hybrid")

    @property
    def query_intent(self) -> Dict[str, Any]:
        """Get query intent with safe fallback."""
        return self.__dict__.get("query_intent", {})

    @property
    def vector_store(self) -> Chroma:
        """Get vector store."""
        return self.__dict__.get("vector_store")

    def _get_relevant_documents(
        self, query: str, *, run_manager: Any = None
    ) -> List[Document]:
        """
        Retrieve relevant documents using hybrid search.

        Args:
            query: The search query
            run_manager: Optional callback manager

        Returns:
            List of relevant documents ranked by RRF
        """
        # Determine search strategy based on query type
        if self.query_type == "list":
            return self._list_query(query)
        elif self.query_type == "filter":
            return self._metadata_only_query(query)
        else:
            # Hybrid or semantic search
            return self._hybrid_search(query)

    def _list_query(self, query: str) -> List[Document]:
        """
        Handle list queries (e.g., "What ADRs do we have?", "List all accepted ADRs").
        Uses metadata filtering only, no semantic search needed.
        """
        filter_dict = self._build_metadata_filter()
        
        # If author filter is present, retrieve more documents since we'll filter in Python
        limit = settings.LIST_QUERY_LIMIT
        if self.query_intent.get("author"):
            limit = limit * 3  # Get more candidates for author filtering
        
        # Get all documents matching the filter with error handling
        try:
            if filter_dict:
                # Use ChromaDB's where filter to get matching documents
                results = self.vector_store._collection.get(
                    where=filter_dict,
                    limit=limit,
                )
            else:
                # No filter - get all documents
                results = self.vector_store._collection.get(limit=limit)
        except Exception as e:
            print(f"Error retrieving documents from ChromaDB: {e}")
            return []

        # Convert to Document objects with safe indexing
        documents = self._safe_convert_chromadb_results(results)

        # Apply author filter if specified (post-retrieval since ChromaDB doesn't support regex)
        documents = self._filter_by_author(documents)

        return documents

    def _metadata_only_query(self, query: str) -> List[Document]:
        """
        Handle metadata-only filter queries (e.g., "ADRs by author X").
        Uses metadata filtering with optional keyword matching.
        """
        filter_dict = self._build_metadata_filter()
        
        if not filter_dict:
            # No metadata filters - fall back to hybrid search
            return self._hybrid_search(query)

        # If author filter is present, retrieve more documents since we'll filter in Python
        limit = settings.RETRIEVAL_K * 2
        if self.query_intent.get("author"):
            limit = limit * 2  # Get even more candidates for author filtering
        
        # Get documents matching metadata filters with error handling
        try:
            results = self.vector_store._collection.get(
                where=filter_dict,
                limit=limit,
            )
        except Exception as e:
            print(f"Error retrieving documents from ChromaDB: {e}")
            return []

        # Convert to Document objects with safe indexing
        documents = self._safe_convert_chromadb_results(results)

        # Apply author filter if specified (post-retrieval since ChromaDB doesn't support regex)
        documents = self._filter_by_author(documents)

        # If query has keywords, apply BM25 ranking
        if query.strip() and len(documents) > 0:
            documents = self._apply_bm25_ranking(query, documents)

        return documents[: settings.RETRIEVAL_K]

    def _hybrid_search(self, query: str) -> List[Document]:
        """
        Perform true hybrid search combining vector similarity and BM25 keyword search.
        Uses Reciprocal Rank Fusion (RRF) to merge results.
        """
        filter_dict = self._build_metadata_filter()

        # 1. Vector similarity search
        vector_docs = self._vector_search(query, filter_dict)
        
        # 2. BM25 keyword search
        bm25_docs = self._bm25_search(query, filter_dict)

        # 3. Combine results using RRF
        fused_docs = self._reciprocal_rank_fusion(vector_docs, bm25_docs)

        # Apply author filter if specified (post-retrieval since ChromaDB doesn't support regex)
        fused_docs = self._filter_by_author(fused_docs)

        return fused_docs[: settings.RETRIEVAL_K]

    def _vector_search(
        self, query: str, filter_dict: Optional[Dict[str, Any]]
    ) -> List[Document]:
        """Perform vector similarity search with error handling."""
        try:
            search_kwargs: Dict[str, Any] = {
                "k": settings.VECTOR_K,
            }
            if filter_dict:
                search_kwargs["filter"] = filter_dict

            retriever = self.vector_store.as_retriever(
                search_type=settings.RETRIEVAL_SEARCH_TYPE,
                search_kwargs=search_kwargs,
            )

            return retriever.invoke(query)
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []

    def _bm25_search(
        self, query: str, filter_dict: Optional[Dict[str, Any]]
    ) -> List[Document]:
        """
        Perform BM25 keyword search.
        First gets candidate documents (with metadata filter if provided),
        then ranks them using BM25.
        """
        # If author filter is present, retrieve more documents since we'll filter in Python
        bm25_limit = settings.BM25_K * 3
        if self.query_intent.get("author"):
            bm25_limit = bm25_limit * 2  # Get more candidates for author filtering
        
        # Get candidate documents from vector store with error handling
        try:
            if filter_dict:
                results = self.vector_store._collection.get(
                    where=filter_dict,
                    limit=bm25_limit,
                )
            else:
                # Get a larger set of candidates for BM25
                results = self.vector_store._collection.get(limit=bm25_limit)
        except Exception as e:
            print(f"Error retrieving documents for BM25 search: {e}")
            return []

        # Convert to Document objects with safe indexing
        documents = self._safe_convert_chromadb_results(results)

        # Filter out documents with empty content before BM25
        documents = [doc for doc in documents if doc.page_content and doc.page_content.strip()]

        if not documents:
            return []

        # Build document corpus for BM25
        corpus = []
        valid_documents = []
        for doc in documents:
            tokens = self._tokenize(doc.page_content)
            # Only include documents with non-empty token lists
            if tokens:
                corpus.append(tokens)
                valid_documents.append(doc)

        if not corpus or not valid_documents:
            return []

        # Initialize BM25 and rank
        try:
            bm25 = BM25Okapi(corpus)
            query_tokens = self._tokenize(query)
            if not query_tokens:
                # If query has no valid tokens, return documents as-is
                return valid_documents[: settings.BM25_K]
            
            scores = bm25.get_scores(query_tokens)

            # Sort documents by BM25 scores
            scored_docs = list(zip(valid_documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            # Return top K documents
            return [doc for doc, score in scored_docs[: settings.BM25_K]]
        except Exception as e:
            print(f"Error in BM25 ranking: {e}")
            # Fallback: return documents as-is if BM25 fails
            return valid_documents[: settings.BM25_K]

    def _reciprocal_rank_fusion(
        self, vector_docs: List[Document], bm25_docs: List[Document]
    ) -> List[Document]:
        """
        Combine results from vector and BM25 search using Reciprocal Rank Fusion (RRF).
        RRF is an industry-standard method for combining ranked lists.

        Formula: RRF(d) = sum(1 / (k + rank(d, list_i))) for all lists i
        """
        # Create document ID mapping to avoid duplicates
        doc_scores: Dict[str, float] = defaultdict(float)
        doc_map: Dict[str, Document] = {}

        # Score vector search results
        for rank, doc in enumerate(vector_docs, start=1):
            doc_id = self._get_doc_id(doc)
            doc_map[doc_id] = doc
            doc_scores[doc_id] += 1.0 / (settings.RRF_K + rank)

        # Score BM25 search results
        for rank, doc in enumerate(bm25_docs, start=1):
            doc_id = self._get_doc_id(doc)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
            doc_scores[doc_id] += 1.0 / (settings.RRF_K + rank)

        # Sort by combined RRF score
        sorted_docs = sorted(
            doc_scores.items(), key=lambda x: x[1], reverse=True
        )

        # Return documents in order
        return [doc_map[doc_id] for doc_id, score in sorted_docs]

    def _build_metadata_filter(self) -> Optional[Dict[str, Any]]:
        """
        Build ChromaDB metadata filter from query intent.
        Supports: technologies, domain, status, date ranges.
        Note: Author filtering is done post-retrieval in Python since ChromaDB doesn't support regex.
        """
        filter_conditions: List[Dict[str, Any]] = []

        # Technology filters (one-hot encoded)
        # Use the same normalization as during storage to ensure consistent matching
        if self.query_intent.get("technologies"):
            technologies: List[str] = self.query_intent["technologies"]
            for tech in technologies:
                normalized_tech = normalize_technology_name(tech)
                filter_conditions.append({f"tech_{normalized_tech}": {"$eq": True}})

        # Domain filter - normalize for consistent matching
        if self.query_intent.get("domain"):
            domain: str = self.query_intent["domain"]
            normalized_domain = normalize_domain(domain)
            filter_conditions.append({"domain": {"$eq": normalized_domain}})

        # Note: Author filter is NOT included here - it's applied post-retrieval
        # ChromaDB doesn't support $regex, so we filter by author in Python

        # Status filter - normalize for consistent matching
        if self.query_intent.get("status"):
            status: str = self.query_intent["status"]
            normalized_status = normalize_status(status)
            filter_conditions.append({"status": {"$eq": normalized_status}})

        # Date range filters with validation
        date_filters = []
        if self.query_intent.get("date_from"):
            date_from = self.query_intent["date_from"]
            validated_date = self._validate_and_format_date(date_from, is_start=True)
            if validated_date:
                date_filters.append({"date": {"$gte": validated_date}})

        if self.query_intent.get("date_to"):
            date_to = self.query_intent["date_to"]
            validated_date = self._validate_and_format_date(date_to, is_start=False)
            if validated_date:
                date_filters.append({"date": {"$lte": validated_date}})

        if date_filters:
            if len(date_filters) == 2:
                filter_conditions.append({"$and": date_filters})
            else:
                filter_conditions.extend(date_filters)

        # Combine all conditions
        if not filter_conditions:
            return None

        if len(filter_conditions) == 1:
            return filter_conditions[0]

        return {"$and": filter_conditions}

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization for BM25.
        Splits on whitespace and converts to lowercase.
        """
        # Remove punctuation and split
        text = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = text.split()
        # Filter out very short tokens
        return [token for token in tokens if len(token) > 2]

    def _get_doc_id(self, doc: Document) -> str:
        """
        Generate a unique ID for a document.
        Uses metadata fields to create a stable ID.
        """
        # Use filename + chunk index if available, otherwise use content hash
        if "filename" in doc.metadata:
            chunk_id = doc.metadata.get("chunk_index", "0")
            return f"{doc.metadata['filename']}_{chunk_id}"
        # Fallback: use first 100 chars of content as ID
        return doc.page_content[:100]

    def _apply_bm25_ranking(
        self, query: str, documents: List[Document]
    ) -> List[Document]:
        """
        Apply BM25 ranking to a list of documents.
        Used for metadata-only queries that also need keyword ranking.
        """
        if not documents:
            return []

        # Filter out documents with empty content
        valid_docs = [doc for doc in documents if doc.page_content and doc.page_content.strip()]
        if not valid_docs:
            return []

        # Build corpus with non-empty token lists
        corpus = []
        valid_documents = []
        for doc in valid_docs:
            tokens = self._tokenize(doc.page_content)
            if tokens:  # Only include documents with valid tokens
                corpus.append(tokens)
                valid_documents.append(doc)

        if not corpus or not valid_documents:
            return valid_documents  # Return as-is if no valid corpus

        try:
            bm25 = BM25Okapi(corpus)
            query_tokens = self._tokenize(query)
            if not query_tokens:
                return valid_documents  # Return as-is if query has no tokens
            
            scores = bm25.get_scores(query_tokens)

            scored_docs = list(zip(valid_documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            return [doc for doc, score in scored_docs]
        except Exception as e:
            print(f"Error in BM25 ranking: {e}")
            return valid_documents  # Fallback: return documents as-is

    def _filter_by_author(self, documents: List[Document]) -> List[Document]:
        """
        Filter documents by author name (case-insensitive partial matching).
        This is done post-retrieval since ChromaDB doesn't support regex in where clauses.

        Args:
            documents: List of documents to filter

        Returns:
            Filtered list of documents matching the author filter
        """
        if not self.query_intent.get("author"):
            return documents

        author_filter = self.query_intent["author"].lower().strip()
        if not author_filter:
            return documents

        filtered_docs = []
        for doc in documents:
            author = doc.metadata.get("author", "").lower()
            # Case-insensitive partial matching
            if author_filter in author or author in author_filter:
                filtered_docs.append(doc)

        return filtered_docs

    def _safe_convert_chromadb_results(
        self, results: Optional[Dict[str, Any]]
    ) -> List[Document]:
        """
        Safely convert ChromaDB results to Document objects with proper bounds checking.

        Args:
            results: ChromaDB get() results dictionary

        Returns:
            List of Document objects
        """
        documents = []
        
        if not results:
            return documents

        # Check if results has the expected structure
        if not isinstance(results, dict):
            return documents

        ids = results.get("ids", [])
        if not ids or not isinstance(ids, list):
            return documents

        metadatas = results.get("metadatas", [])
        doc_contents = results.get("documents", [])

        # Ensure all lists have the same length or handle mismatches
        max_len = len(ids)
        if metadatas and isinstance(metadatas, list):
            max_len = min(max_len, len(metadatas))
        if doc_contents and isinstance(doc_contents, list):
            max_len = min(max_len, len(doc_contents))

        # Safely iterate with bounds checking
        for i in range(max_len):
            doc_id = ids[i] if i < len(ids) else None
            metadata = metadatas[i] if (metadatas and i < len(metadatas)) else {}
            content = doc_contents[i] if (doc_contents and i < len(doc_contents)) else ""
            
            # Ensure metadata is a dict
            if not isinstance(metadata, dict):
                metadata = {}
            
            # Ensure content is a string
            if not isinstance(content, str):
                content = str(content) if content is not None else ""

            documents.append(Document(page_content=content, metadata=metadata))

        return documents

    def _validate_and_format_date(self, date_str: str, is_start: bool = True) -> Optional[str]:
        """
        Validate and format date string for ChromaDB filtering.
        Supports formats: YYYY, YYYY-MM, YYYY-MM-DD

        Args:
            date_str: Date string to validate
            is_start: True if this is a start date (defaults to beginning of period),
                     False if end date (defaults to end of period)

        Returns:
            Formatted date string (YYYY-MM-DD) or None if invalid
        """
        if not date_str or not isinstance(date_str, str):
            return None

        date_str = date_str.strip()
        
        # Handle year-only format (YYYY)
        if len(date_str) == 4 and date_str.isdigit():
            year = int(date_str)
            if 1900 <= year <= 2100:  # Reasonable year range
                if is_start:
                    return f"{year}-01-01"
                else:
                    return f"{year}-12-31"
            return None

        # Handle YYYY-MM format
        if len(date_str) == 7 and date_str.count("-") == 1:
            try:
                parts = date_str.split("-")
                year = int(parts[0])
                month = int(parts[1])
                if 1900 <= year <= 2100 and 1 <= month <= 12:
                    if is_start:
                        return f"{year}-{month:02d}-01"
                    else:
                        # Get last day of month
                        from calendar import monthrange
                        last_day = monthrange(year, month)[1]
                        return f"{year}-{month:02d}-{last_day:02d}"
            except (ValueError, IndexError):
                return None

        # Handle YYYY-MM-DD format
        if len(date_str) == 10 and date_str.count("-") == 2:
            try:
                # Validate date format
                datetime.strptime(date_str, "%Y-%m-%d")
                return date_str
            except ValueError:
                return None

        # Try to parse other common formats
        try:
            # Try ISO format
            parsed_date = datetime.fromisoformat(date_str.replace(" ", "T"))
            return parsed_date.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            pass

        # If we can't parse it, return None
        return None

