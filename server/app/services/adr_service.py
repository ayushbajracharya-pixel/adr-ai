from fastapi import HTTPException
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import chromadb
import re
from app.utils.text_cleaner import (
    clean_text_from_bullets,
    one_hot_encode_lists_in_dict,
)


from langchain.schema import Document
import pypdfium2 as pdfium
import docx
from io import BytesIO
from typing import Dict, List
from botocore.exceptions import ClientError

from app.config.settings import settings
from app.models.schemas import QueryIntent
from app.services.retrieval_service import get_hybrid_retriever
from app.services.uploader_service import UploaderService
from app.chains.extraction_chain import ExtractionChain
from app.constants.misc_constants import canonical_headings_map

collection_name = "adr_collection"


class ADRService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.client = chromadb.HttpClient(host="chromadb", port=8000)
        self.vector_store = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embeddings,
        )
        self.llm = ChatOpenAI(
            model="gpt-4.1-nano",
            temperature=0.1,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.extraction_chain = ExtractionChain()
        self.uploader_service = UploaderService()

    async def process_adr(self, file):
        """Process uploaded ADR and add to knowledge base"""

        file_name = file.filename
        content = await file.read()

        # Step 1: Upload to S3 with specific error handling
        s3_uri = None
        public_url = None
        try:
            s3_object_name = f"adr_uploads/{file_name}"
            with BytesIO(content) as file_obj:
                uploadResponse = self.uploader_service.upload_fileobj(
                    file_obj, s3_object_name
                )
                s3_uri = uploadResponse.get("s3_uri")
                public_url = uploadResponse.get("public_url")
                if not s3_uri:
                    raise IOError("S3 upload returned a malformed response.")
            print(f"Successfully uploaded {file_name} to S3.")
        except Exception as e:
            # Catch any issues with S3 connection, permissions, etc.
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file to S3: {e}"
            )

        # Step 2: Extract text and handle potential errors
        try:
            text_content = clean_text_from_bullets(
                self._extract_text_from_file_content(content, file_name)
            )
        except Exception as e:
            # Catch errors during text extraction from the file content
            # You might want to log this error and potentially delete the S3 object.
            # self.uploader_service.delete_object(s3_object_name)
            raise HTTPException(
                status_code=500, detail=f"Failed to extract text from document: {e}"
            )

        # Step 3: Extract and transform metadata
        try:
            extracted_metadata = self.extraction_chain.invoke_metadata_chain(
                {"text": text_content}
            )
            extracted_metadata["filename"] = file_name
            extracted_metadata["source"] = file_name
            extracted_metadata["s3_uri"] = s3_uri
            extracted_metadata["public_url"] = public_url

            transformed_metadata = one_hot_encode_lists_in_dict(extracted_metadata)

        except Exception as e:
            # Handle potential failures from the LLM extraction chain
            raise HTTPException(
                status_code=500, detail=f"Failed to extract metadata from document: {e}"
            )

        # Step 4: Split and store documents in the vector store
        try:
            # We can clean the text by removing the short info like status, date, etc. which are already present in the metadata
            # so that our chunks contain only meaningful information.

            # Get dynamic separators based on the specific document
            dynamic_separators = self._get_dynamic_separators(text_content)

            # Initialize the splitter with the dynamic separators
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200, separators=dynamic_separators
            )

            document = Document(
                page_content=text_content, metadata=transformed_metadata
            )
            splits = text_splitter.split_documents([document])

            # Ensure all chunks have metadata
            for split in splits:
                split.metadata.update(transformed_metadata)

            doc_ids = self.vector_store.add_documents(splits)

            # Return all document IDs
            return doc_ids

        except Exception as e:
            # Handle failures during vector store indexing
            raise HTTPException(
                status_code=500, detail=f"Failed to index document in vector store: {e}"
            )

    async def query_adr(self, query: str) -> Dict:
        """
        Main function to process a user query, extract intent,
        perform hybrid retrieval, and generate a comprehensive response.
        """
        # Step 1: Extract intent using the LLM chain
        try:
            intent_info = self.extraction_chain.invoke_intent_chain({"query": query})
            print(f"Extracted Intent: {intent_info.model_dump()}")
        except Exception as e:
            # Fallback to simple retrieval if intent extraction fails
            print(f"Intent extraction failed: {e}. Falling back to basic search.")
            intent_info = QueryIntent(
                technologies=[], requirements=[], compliance_needs=[]
            )

        # Step 2: Perform hybrid retrieval based on the extracted intent
        retriever = get_hybrid_retriever(self.vector_store, intent_info.model_dump())
        retrieved_docs = retriever.invoke(query)

        if not retrieved_docs:
            return {
                "query": query,
                "response": "Sorry, there has been no such implementations.",
            }

        # Step 3: Create the enhanced prompt using the intent info
        prompt_template = self._create_enhanced_prompt(intent_info)

        # Format the retrieved documents for the prompt context
        context_str = self._format_docs(retrieved_docs)

        # Step 4: Generate the final response using the RAG chain
        rag_chain = (
            {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
            | prompt_template
            | self.llm
            | StrOutputParser()
        )

        response_text = rag_chain.invoke({"context": context_str, "question": query})

        # Step 5: Process and format the references
        references = self._create_enhanced_references(retrieved_docs)

        # Combine the generated response and references
        return {"query": query, "response": response_text, "references": references}

    async def delete_file(self, object_key: str):
        # object_key = "adr_uploads/ADR-0001_ Use Kafka for Messaging in Microservices Architecture.pdf"
        try:
            s3_uri = self.uploader_service.get_s3_uri(object_key)
            self.vector_store.delete(where={"s3_uri": s3_uri})
            print(
                f"✅ Successfully deleted documents for '{object_key}' from ChromaDB."
            )

        except Exception as e:
            # Note: If this fails, the file is already gone from S3.
            # We raise a different error to indicate a partial failure.
            raise HTTPException(
                status_code=500,
                detail=f"Vector store deletion failed: {e}. File was successfully removed from S3, but its index data remains. You may need to manually re-index.",
            )

        try:
            s3_deleted = self.uploader_service.delete_file(object_key)
            if not s3_deleted:
                # The uploader_service handles its own error logging, so we just raise here.
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete file from S3 with object key: {object_key}.",
                )
        except ClientError as e:
            # Catch specific Boto3 client errors (e.g., permissions issues, file not found).
            # We re-raise it as an HTTPException for FastAPI to handle.
            raise HTTPException(
                status_code=500, detail=f"S3 deletion failed due to a client error: {e}"
            )
        except Exception as e:
            # Catch any other unexpected errors during the S3 operation.
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred during S3 deletion: {e}",
            )

        return {"object_key": object_key}

    def _extract_text_from_pdf(self, file_obj: BytesIO) -> str:
        """Extract text from PDF using pypdfium2 from an in-memory object."""
        try:
            # pypdfium2's PdfDocument can directly accept a file-like object (BytesIO)
            pdf = pdfium.PdfDocument(file_obj)
            text_content = []

            for page_num in range(len(pdf)):
                page = pdf[page_num]
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                text_content.append(text)

                # Clean up
                textpage.close()
                page.close()

            pdf.close()
            return "\n".join(text_content)

        except Exception as e:
            raise Exception(f"Failed to extract PDF text: {str(e)}")

    def _extract_text_from_docx(self, file_obj: BytesIO) -> str:
        """Extract text from Word document from an in-memory object."""
        try:
            # python-docx's Document can also accept a file-like object
            doc = docx.Document(file_obj)
            text_content = []

            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)

            return "\n".join(text_content)

        except Exception as e:
            raise Exception(f"Failed to extract Word document text: {str(e)}")

    def _extract_text_from_file_content(
        self, file_content: bytes, filename: str
    ) -> str:
        """Extract text based on file extension from in-memory content."""

        file_ext = filename.lower().split(".")[-1]

        # Create an in-memory file object from the binary content.
        # This is a key step to make file-path-based libraries work.
        file_obj = BytesIO(file_content)

        if file_ext == "pdf":
            return self._extract_text_from_pdf(file_obj)
        elif file_ext in ["docx", "doc"]:
            return self._extract_text_from_docx(file_obj)
        elif file_ext in ["txt", "md"]:
            # For text files, we can just decode the bytes directly.
            return file_content.decode("utf-8")
        else:
            raise Exception(f"Unsupported file format: {file_ext}")

    def _create_enhanced_prompt(self, intent_info: QueryIntent) -> ChatPromptTemplate:
        """Creates a contextual prompt template for generation."""
        # This is where you insert your well-crafted prompt instructions
        base_prompt = """
        You are an expert AI assistant helping with technology decisions based on Architecture Decision Records (ADRs) from past projects.

        Context from ADRs:
        {context}

        User Query: {question}

        ANALYSIS: The user is asking about a new project with these characteristics:
        """

        if intent_info.use_case:
            base_prompt += f"- Use Case: {intent_info.use_case}\n"

        if intent_info.domain:
            base_prompt += f"- Domain/Industry: {intent_info.domain}\n"

        if intent_info.requirements:
            base_prompt += (
                f"- Key Requirements: {', '.join(intent_info.requirements)}\n"
            )

        if intent_info.technologies:
            base_prompt += (
                f"- Relevant Technologies: {', '.join(intent_info.technologies)}\n"
            )

        if intent_info.compliance_needs:
            base_prompt += f"- Compliance Considerations: {', '.join(intent_info.compliance_needs)}\n"

        base_prompt += """

        INSTRUCTIONS:
        Based on the provided context, generate a detailed and comprehensive answer to the user's query.
        Format the entire response as a single, valid HTML block. Do not include any text outside of the HTML tags.
        Use appropriate HTML tags for headings (<h2>, <h3>), paragraphs (<p>), lists (<ul>, <li>), and bolding (<b> or <strong>).
        Ensure the response is clean and ready to be rendered in a web browser.

        If no relevant ADRs are found in the context, your response should be a simple HTML paragraph:
        <p>Sorry, there has been such implementations.</p>
        """
        return ChatPromptTemplate.from_template(base_prompt)

    def _format_docs(self, docs: List[Document]) -> str:
        """Formats retrieved documents into a single string for the prompt."""
        formatted = ""
        for doc in docs:
            metadata = doc.metadata
            formatted += f"--- ADR: {metadata.get('title', 'Unknown Title')} ({metadata.get('adr_number', 'Unknown')}) ---\n"
            formatted += f"Source: {metadata.get('source', 'N/A')}\n"
            formatted += f"Content: {doc.page_content}\n\n"
        return formatted

    def _create_enhanced_references(self, docs: List[Document]) -> List[Dict]:
        """Creates unique, detailed references from retrieved documents."""
        references = []
        seen_files = set()

        # A simple way to get unique documents, more advanced scoring can be added here
        unique_docs = []
        for doc in docs:
            if doc.metadata.get("filename") not in seen_files:
                unique_docs.append(doc)
                seen_files.add(doc.metadata.get("filename"))

        for doc in unique_docs:
            metadata = doc.metadata
            ref = {
                "filename": metadata.get("filename", "Unknown"),
                "adr_number": metadata.get("adr_number", "Unknown"),
                "title": metadata.get("title", "Unknown Title"),
                "status": metadata.get("status", "Unknown"),
                "author": metadata.get("author", "Unknown"),
                "date": metadata.get("date", "Unknown"),
                "source": metadata.get("source", "N/A"),
                "public_url": metadata.get("public_url", "Unknown"),
                "s3_uri": metadata.get("s3_uri", "Unknown"),
            }
            references.append(ref)
        return references

    def _get_dynamic_separators(self, text_content: str) -> list[str]:
        """
        Dynamically generates a list of separators based on recognized ADR section headings.
        This version uses a single, cleaner data structure to manage canonical headings and synonyms.

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
