"""Vector store service for managing document storage."""
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
import chromadb
from typing import List, Dict, Any
import re

from app.core.config import settings
from app.utils.constants import canonical_headings_map

collection_name = "adr_collection"


class VectorStoreService:
    """Manages vector store operations."""

    def __init__(self):
        """Initialize the vector store service."""
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.client = chromadb.HttpClient(
            host=settings.CHROMADB_HOST, port=settings.CHROMADB_PORT
        )
        self.vector_store = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embeddings,
        )

    def add_documents(
        self, text_content: str, metadata: Dict[str, Any]
    ) -> List[str]:
        """
        Split text into chunks and add to vector store.

        Args:
            text_content: The text content to split and store
            metadata: Metadata to attach to all chunks

        Returns:
            List of document IDs added to the vector store
        """
        # Get dynamic separators based on the specific document
        dynamic_separators = self._get_dynamic_separators(text_content)

        # Initialize the splitter with the dynamic separators
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=dynamic_separators,
        )

        document = Document(page_content=text_content, metadata=metadata)
        splits = text_splitter.split_documents([document])

        # Ensure all chunks have metadata
        for split in splits:
            split.metadata.update(metadata)

        doc_ids = self.vector_store.add_documents(splits)
        return doc_ids

    def delete_documents_by_s3_uri(self, s3_uri: str) -> None:
        """
        Delete documents from vector store by S3 URI.

        Args:
            s3_uri: The S3 URI to filter by
        """
        self.vector_store.delete(where={"s3_uri": s3_uri})

    def _get_dynamic_separators(self, text_content: str) -> List[str]:
        """
        Dynamically generates a list of separators based on recognized ADR section headings.

        Args:
            text_content: The full text content of the ADR document.

        Returns:
            A list of separators to be used by the text splitter.
        """
        found_separators = []

        for canonical_heading, synonyms in canonical_headings_map.items():
            # Create a regex pattern to find any of the synonyms for the current canonical heading.
            # This makes it case-insensitive and handles potential whitespace.
            pattern = r"^\s*(" + "|".join([re.escape(s) for s in synonyms]) + r")\s*$"

            if re.search(pattern, text_content, re.MULTILINE | re.IGNORECASE):
                # If any synonym is found, use the canonical heading to create the separator.
                separator = f"\n\n{canonical_heading}\n\n"
                if separator not in found_separators:
                    found_separators.append(separator)

        # Add general fallbacks to ensure chunks are created even if no headings are found.
        found_separators.extend(["\n\n", "\n", ". ", " "])

        return found_separators

