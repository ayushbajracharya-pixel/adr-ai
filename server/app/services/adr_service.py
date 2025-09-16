from fastapi import HTTPException
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import chromadb

from langchain.schema import Document
import pypdfium2 as pdfium
import docx
import re
from io import BytesIO
from typing import Dict, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError

from app.config.settings import settings
from app.models.schemas import QueryIntent
from app.services.intent_service import get_intent_extraction_chain
from app.services.retrieval_service import get_hybrid_retriever
from app.services.uploader_service import UploaderService


# Initialize your UploaderService. It will automatically use the settings.
uploader_service = UploaderService()
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
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ". ", " "]
        )
        self.intent_chain = get_intent_extraction_chain()

    async def process_adr(self, file):
        """Process uploaded ADR and add to knowledge base"""

        # Define the S3 object name (e.g., in a 'raw_uploads' folder)
        s3_object_name = f"adr_uploads/{file.filename}"

        try:
            content = await file.read()

            # Create an in-memory file-like object from the content.
            file_obj = BytesIO(content)

            # Use the UploaderService to upload the in-memory object directly to S3.
            uploadResponse = uploader_service.upload_fileobj(file_obj, s3_object_name)
            s3_uri = uploadResponse["s3_uri"]
            public_url = uploadResponse["public_url"]

            if not s3_uri:
                print("Failed to upload file to S3.")
                return None  # Or handle the error as appropriate

            print(f"Successfully uploaded {file.filename} to S3.")

            # Extract text using pypdfium2 or other extractors
            text_content = self._extract_text_from_file_content(content, file.filename)

            # Extract metadata
            metadata = self._extract_adr_metadata(
                text_content, file.filename, public_url, s3_uri
            )

            # Create document with metadata
            document = Document(page_content=text_content, metadata=metadata)

            # Split and store
            splits = self.text_splitter.split_documents([document])

            # Ensure all chunks have metadata
            for split in splits:
                split.metadata.update(metadata)

            doc_ids = self.vector_store.add_documents(splits)

            # Return all document IDs
            return doc_ids

        except (ClientError, NoCredentialsError) as e:
            # Handle errors related to S3 operations
            print(f"S3 upload error: {e}")
            return None

    async def query_adr(self, query: str) -> Dict:
        """
        Main function to process a user query, extract intent,
        perform hybrid retrieval, and generate a comprehensive response.
        """
        # Step 1: Extract intent using the LLM chain
        try:
            intent_info = self.intent_chain.invoke({"query": query})
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
            s3_uri = uploader_service.get_s3_uri(object_key)
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
            s3_deleted = uploader_service.delete_file(object_key)
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

    def _extract_adr_metadata(
        self, text: str, filename: str, public_url: str, s3_uri: str
    ) -> dict:
        """Extract metadata from ADR content - works with both markdown and flattened PDF/DOCX text"""
        metadata = {
            "filename": filename,
            "source": filename,
            "document_type": "ADR",
            "public_url": public_url,
            "s3_uri": s3_uri,
        }

        # Clean up text - handle both \n and actual newlines
        text_clean = text.replace("\\n", "\n")
        lines = text_clean.split("\n")

        # Extract title (first line or line containing ADR-XXXX)
        title = self._extract_title(text_clean, lines)
        if title:
            metadata["title"] = title
            # Extract ADR number
            adr_match = re.search(r"ADR-(\d+)", title)
            if adr_match:
                metadata["adr_number"] = adr_match.group(1)

        # Extract basic fields (works for both formats)
        metadata.update(self._extract_basic_fields(text_clean))

        # Extract decision makersing_function=self.embeddings,
        decision_makers = self._extract_decision_makers(text_clean)
        if decision_makers:
            for dm in decision_makers:
                metadata[f"decision_maker_{dm.lower()}"] = True

        # Extract technologies mentioned
        mentioned_technologies = self._extract_technologies_from_text(text_clean)
        if mentioned_technologies:
            for tech in mentioned_technologies:
                metadata[f"tech_{tech.lower()}"] = True

        return metadata

    def _extract_title(self, text: str, lines: List[str]) -> Optional[str]:
        """Extract title from various formats"""
        # Method 1: First line if it contains ADR-
        if lines and "ADR-" in lines[0]:
            return lines[0].strip()

        # Method 2: Look for title pattern in first few lines
        for line in lines[:5]:
            if "ADR-" in line and any(
                word in line.lower() for word in ["use", "implement", "choose", "adopt"]
            ):
                return line.strip()

        # Method 3: Regex pattern for ADR title
        title_match = re.search(r"(ADR-\d+:.*?)(?:\n|$)", text)
        if title_match:
            return title_match.group(1).strip()

        return None

    def _extract_basic_fields(self, text: str) -> Dict:
        """Extract status, date, author fields"""
        fields = {}

        # Status - look for "Status" followed by value on next line or after colon
        status_patterns = [
            r"Status\s*\n\s*([^\n]+)",  # Status on one line, value on next
            r"Status:\s*([^\n]+)",  # Status: Value
            r"Status\s+([^\n]+)",  # Status Value
        ]
        for pattern in status_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields["status"] = match.group(1).strip()
                break

        # Date
        date_patterns = [
            r"Date\s*\n\s*([^\n]+)",
            r"Date:\s*([^\n]+)",
            r"Date\s+([^\n]+)",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields["date"] = match.group(1).strip()
                break

        # Author
        author_patterns = [
            r"Author\s*\n\s*([^\n]+)",
            r"Author:\s*([^\n]+)",
            r"Author\s+([^\n]+)",
        ]
        for pattern in author_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields["author"] = match.group(1).strip()
                break

        return fields

    def _extract_decision_makers(self, text: str) -> List[str]:
        """Extract decision makers list"""
        decision_makers = []

        # Find the Decision Makers section
        patterns = [  # Filter by technologies using boolean flags
            # Example: If technologies are ['kafka', 'sqs'], this will create
            # {'tech_kafka': {'$eq': True}} and {'tech_sqs': {'$eq': True}}
            r"Decision Makers\s*\n(.*?)(?=\n[A-Z][a-z]+\s*\n|\n\n|\Z)",  # Until next section
            r"Decision Makers:\s*\n(.*?)(?=\n[A-Z][a-z]+\s*\n|\n\n|\Z)",
            r"Decision Makers\s*\n(.*?)(?=Context|Decision|Status|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                makers_text = match.group(1).strip()

                # Split by newlines and clean
                for line in makers_text.split("\n"):
                    line_clean = line.strip()
                    if line_clean and not line_clean.lower().startswith(
                        ("context", "decision", "status")
                    ):
                        # Remove bullet points or dashes
                        line_clean = re.sub(r"^[-•*]\s*", "", line_clean)
                        if line_clean:
                            decision_makers.append(line_clean)
                break

        return decision_makers

    def _extract_technologies_from_text(self, text: str) -> List[str]:
        """Extract technology names mentioned in the ADR"""
        tech_patterns = [
            r"\bkafka\b",
            r"\brabbitmq\b",
            r"\baws\s+sqs\b",
            r"\bsqs\b",
            r"\bmicroservices\b",
            r"\bmsk\b",
            r"\bzookeeper\b",
            r"\bkraft\b",
            r"\bamqp\b",
            r"\bkafka\s+connect\b",
            r"\bkafka\s+streams\b",
            r"\bksqldb\b",
            r"\bevent\s+streaming\b",
            r"\bmessaging\b",
            # GenAI patterns
            r"\blangchain\b",
            r"\bllama\b",
            r"\bgpt-?\d*\b",
            r"\bclaude\b",
            r"\blangraph\b",
            r"\bopenai\b",
            r"\bhuggingface\b",
            r"\btransformers\b",
            r"\btext-to-speech\b",
            r"\btts\b",
            r"\bspeech-to-text\b",
            r"\bstt\b",
            r"\bembedding\b",
            r"\bvector\s+database\b",
            r"\brag\b",
            r"\bllm\b",
        ]

        found_techs = set()
        text_lower = text.lower()

        for pattern in tech_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            found_techs.update(matches)

        return list(found_techs)

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
