"""Main ADR service orchestrator."""
from fastapi import HTTPException, UploadFile
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from io import BytesIO
from botocore.exceptions import ClientError

from app.services.adr.document_processor import DocumentProcessor
from app.services.adr.metadata_extractor import MetadataExtractor
from app.services.adr.vector_store_service import VectorStoreService
from app.services.adr.query_processor import QueryProcessor
from app.services.adr.response_generator import ResponseGenerator
from app.services.storage.s3_service import S3Service
from app.domain.schemas.query import QueryIntent


class ADRService:
    """Main orchestrator for ADR processing and querying."""

    def __init__(self) -> None:
        """Initialize the ADRService with all required services."""
        self.vector_store_service = VectorStoreService()
        self.document_processor = DocumentProcessor()
        self.metadata_extractor = MetadataExtractor()
        self.query_processor = QueryProcessor(self.vector_store_service.vector_store)
        self.response_generator = ResponseGenerator()
        self.s3_service = S3Service()

    async def process_adr(
        self, file: UploadFile
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Process uploaded ADR and add to knowledge base.

        Args:
            file: The uploaded file to process

        Returns:
            Tuple of (List of document IDs added to the vector store, File information dict)

        Raises:
            HTTPException: If any step of processing fails
        """
        file_name = file.filename
        if not file_name:
            raise HTTPException(status_code=400, detail="File must have a filename")

        content = await file.read()

        # Step 1: Upload to S3
        s3_uri = None
        public_url = None
        try:
            s3_object_name = f"adr_uploads/{file_name}"
            with BytesIO(content) as file_obj:
                upload_response = self.s3_service.upload_fileobj(
                    file_obj, s3_object_name
                )
                s3_uri = upload_response.get("s3_uri")
                public_url = upload_response.get("public_url")
                if not s3_uri:
                    raise IOError("S3 upload returned a malformed response.")
            print(f"Successfully uploaded {file_name} to S3.")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file to S3: {e}"
            )

        # Step 2: Extract text
        try:
            text_content = self.document_processor.extract_text_from_content(content, file_name)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to extract text from document: {e}"
            )

        # Step 3: Extract and transform metadata
        try:
            transformed_metadata = self.metadata_extractor.extract_and_transform_metadata(
                text_content, file_name, s3_uri, public_url
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to extract metadata from document: {e}"
            )

        # Step 4: Split and store documents in the vector store
        try:
            doc_ids = self.vector_store_service.add_documents(
                text_content, transformed_metadata
            )

            # Prepare file information for response
            file_info = {
                "object_key": s3_object_name,
                "filename": file_name,
                "size_bytes": len(content),
                "last_modified": datetime.utcnow().isoformat() + "+00:00",
                "permanent_url": public_url,
            }

            return doc_ids, file_info

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to index document in vector store: {e}"
            )

    async def query_adr(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Main function to process a user query, extract intent,
        perform hybrid retrieval, and generate a comprehensive response.

        Args:
            query: The user's query
            conversation_history: Optional list of previous messages

        Returns:
            Dictionary with query, response, and references
        """
        # Step 0: Validate query quality
        query_validation = self.query_processor.validate_query_quality(
            query, conversation_history
        )
        if not query_validation["is_searchable"]:
            return self.query_processor.generate_conversational_response(
                query, query_validation["reason"], conversation_history
            )

        # Step 1: Extract intent
        intent_info = self.query_processor.extract_intent(query)

        # Step 2: Perform hybrid retrieval
        retrieved_docs = self.query_processor.retrieve_documents(query, intent_info)

        # If no results, generate a helpful "no results" response
        if not retrieved_docs:
            return self._generate_no_results_response(
                query, intent_info, conversation_history
            )

        # Step 3: Generate response
        response_text = self.response_generator.generate_response(
            query, retrieved_docs, intent_info, conversation_history
        )

        # Step 4: Create references
        references = self.response_generator.create_references(retrieved_docs, query=query)

        return {"query": query, "response": response_text, "references": references}

    async def delete_file(self, object_key: str) -> Dict[str, str]:
        """
        Delete a file from both S3 and the vector store.

        Args:
            object_key: The S3 object key to delete

        Returns:
            Dictionary with object_key

        Raises:
            HTTPException: If deletion fails
        """
        try:
            s3_uri = self.s3_service.get_s3_uri(object_key)
            self.vector_store_service.delete_documents_by_s3_uri(s3_uri)
            print(f"✅ Successfully deleted documents for '{object_key}' from ChromaDB.")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Vector store deletion failed: {e}. File was successfully removed from S3, but its index data remains. You may need to manually re-index.",
            )

        try:
            s3_deleted = self.s3_service.delete_file(object_key)
            if not s3_deleted:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete file from S3 with object key: {object_key}.",
                )
        except ClientError as e:
            raise HTTPException(
                status_code=500, detail=f"S3 deletion failed due to a client error: {e}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred during S3 deletion: {e}",
            )

        return {"object_key": object_key}

    def _generate_no_results_response(
        self,
        query: str,
        intent_info: QueryIntent,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a helpful "no results" response with suggestions.
        """
        search_context = f"User Query: {query}\n\n"

        if intent_info.technologies:
            search_context += f"Technologies searched: {', '.join(intent_info.technologies)}\n"
        if intent_info.domain:
            search_context += f"Domain/Industry searched: {intent_info.domain}\n"
        if intent_info.requirements:
            search_context += f"Requirements searched: {', '.join(intent_info.requirements)}\n"

        search_context += "\nNo matching ADRs were found in the knowledge base."

        no_results_prompt = f"""
        You are a helpful AI assistant for an Architecture Decision Records (ADRs) knowledge base.
        
        The user searched for information but no relevant ADRs were found.
        
        Search Details:
        {search_context}
        
        Generate a helpful, empathetic response that:
        1. Acknowledges that no relevant ADRs were found
        2. Suggests ways to reformulate the query (e.g., use different keywords, broader terms, related technologies)
        3. Provide actionable next steps
        4. Maintains a professional but friendly tone
        
        IMPORTANT RESTRICTIONS:
        - DO NOT include any follow-up offers or invitations for further assistance
        - DO NOT include phrases like "If you'd like, I can help...", "Just let me know...", "Feel free to ask...", or similar offers
        - Keep the response focused on the current query and suggestions only
        - End the response after providing the suggestions - do not add any closing offers
        
        Format the entire response as a single, valid HTML block following these requirements:
        - CRITICAL: Generate compact HTML without newline characters (\\n) between tags
        - Use <h2> or <h3> for section headings
        - Use <ul> and <li> for suggestions and lists
        - Use <p> tags for paragraphs
        - Use appropriate emojis: 📌 for suggestions, 💡 for tips, 🔍 for search advice
        - DO NOT include \\n characters anywhere - the HTML should be a single continuous string
        - Write in a clear, conversational style similar to ChatGPT
        
        Example structure:
        <h2>No Matching ADRs Found</h2>
        <p>I couldn't find any ADRs matching your query...</p>
        <h3>Suggestions</h3>
        <ul><li>Try...</li></ul>
        """

        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        prompt_template = ChatPromptTemplate.from_template(no_results_prompt)
        response_chain = prompt_template | self.response_generator.llm | StrOutputParser()
        response_text = response_chain.invoke({})
        response_text = self.response_generator._clean_html_response(response_text)

        return {
            "query": query,
            "response": response_text,
            "references": [],
        }

