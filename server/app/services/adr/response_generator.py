"""Response generation service for query responses."""
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from typing import Dict, List, Optional, Any, Set
from app.core.config import settings
from app.domain.schemas.query import QueryIntent
from app.services.storage.s3_service import S3Service


class ResponseGenerator:
    """Handles response generation for queries."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.s3_service = S3Service()

    def generate_response(
        self,
        query: str,
        retrieved_docs: List[Document],
        intent_info: QueryIntent,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate response text from retrieved documents.

        Args:
            query: The user's query
            retrieved_docs: Retrieved documents
            intent_info: Extracted query intent
            conversation_history: Optional conversation history

        Returns:
            Generated response text
        """
        prompt_template = self._create_enhanced_prompt(intent_info, conversation_history)
        context_str = self._format_docs(retrieved_docs)

        rag_chain = (
            {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
            | prompt_template
            | self.llm
            | StrOutputParser()
        )

        response_text = rag_chain.invoke({"context": context_str, "question": query})
        response_text = self._clean_html_response(response_text)
        return response_text

    def create_references(
        self, docs: List[Document], query: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Create reference list from retrieved documents.

        Args:
            docs: Retrieved documents
            query: Optional query for filtering

        Returns:
            List of reference dictionaries
        """
        references = []
        seen_files: Set[str] = set()

        # Get unique documents
        unique_docs = []
        for doc in docs:
            if doc.metadata.get("filename") not in seen_files:
                unique_docs.append(doc)
                seen_files.add(doc.metadata.get("filename"))

        # Filter references based on relevance if query provided
        if query and unique_docs:
            unique_docs = self._filter_relevant_references(query, unique_docs)

        for doc in unique_docs:
            metadata = doc.metadata
            s3_uri = metadata.get("s3_uri", "Unknown")

            # Regenerate public_url from s3_uri
            public_url = "Unknown"
            if s3_uri != "Unknown" and s3_uri.startswith("s3://"):
                try:
                    parts = s3_uri.replace("s3://", "").split("/", 1)
                    if len(parts) == 2:
                        object_key = parts[1]
                        public_url = self.s3_service.get_public_url(object_key)
                except Exception as e:
                    print(f"Warning: Could not regenerate URL from s3_uri {s3_uri}: {e}")
                    public_url = metadata.get("public_url", "Unknown")
            else:
                public_url = metadata.get("public_url", "Unknown")

            ref = {
                "filename": metadata.get("filename", "Unknown"),
                "adr_number": metadata.get("adr_number", "Unknown"),
                "title": metadata.get("title", "Unknown Title"),
                "status": metadata.get("status", "Unknown"),
                "author": metadata.get("author", "Unknown"),
                "date": metadata.get("date", "Unknown"),
                "source": metadata.get("source", "N/A"),
                "public_url": public_url,
                "s3_uri": s3_uri,
            }
            references.append(ref)
        return references

    def _create_enhanced_prompt(
        self,
        intent_info: QueryIntent,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ChatPromptTemplate:
        """Creates a contextual prompt template for generation."""
        base_prompt = """
        You are an expert AI assistant helping with technology decisions based on Architecture Decision Records (ADRs) from past projects.

        Your job is to answer questions using only the provided ADR context.
        You must be concise, structured, and professional.

        Context from ADRs:
        {context}
        """

        # Add conversation history if available
        if conversation_history:
            base_prompt += "\n\nPrevious Conversation History:\n"
            for msg in conversation_history[-settings.CONVERSATION_HISTORY_LIMIT:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
                if len(content) > settings.MESSAGE_TRUNCATE_LENGTH:
                    content = content[: settings.MESSAGE_TRUNCATE_LENGTH] + "..."
                base_prompt += f"{role}: {content}\n"
            base_prompt += "\n"

        base_prompt += """
        Current User Query: {question}

        ANALYSIS: The user is asking about a new project with these characteristics:
        """

        if intent_info.use_case:
            base_prompt += f"- Use Case: {intent_info.use_case}\n"

        if intent_info.domain:
            base_prompt += f"- Domain/Industry: {intent_info.domain}\n"

        if intent_info.requirements:
            base_prompt += f"- Key Requirements: {', '.join(intent_info.requirements)}\n"

        if intent_info.technologies:
            base_prompt += f"- Relevant Technologies: {', '.join(intent_info.technologies)}\n"

        if intent_info.compliance_needs:
            base_prompt += f"- Compliance Considerations: {', '.join(intent_info.compliance_needs)}\n"

        base_prompt += """

        INSTRUCTIONS:
        Based on the provided context and conversation history, generate a detailed and comprehensive answer to the user's query.
        Consider the conversation history to provide contextually relevant responses that build upon previous discussions.
        
        RESPONSE FORMAT REQUIREMENTS:
        - Format the entire response as a single, valid HTML block. Do not include any text outside of the HTML tags.
        - CRITICAL: Generate compact HTML without newline characters (\\n) between tags. Write the HTML as a continuous string without line breaks.
        - Use clear section headings with <h2> or <h3> tags to organize content logically
        - Use bullet points (<ul> and <li>) for lists, recommendations, and key points - avoid long paragraphs when lists are more appropriate
        - Use appropriate emojis where helpful: 🚀 for recommendations/actions, 📌 for important points, ⚠️ for warnings/cautions, ✅ for confirmations/benefits
        - Use <p> tags for paragraphs, <b> or <strong> for emphasis
        - DO NOT include \\n characters anywhere in your response - the HTML should be a single continuous string
        - DO NOT add unnecessary line breaks or extra whitespace between HTML elements
        - DO NOT invent information that is not present in the provided context
        - DO NOT repeat the same information multiple times - be concise and avoid redundancy
        - Write in a clear, conversational style similar to ChatGPT - professional but approachable
        - Ensure the response is clean and ready to be rendered in a web browser

        If no relevant ADRs are found in the context, your response should be a simple HTML paragraph:
        <p>Sorry, there has been no such implementations.</p>
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

    def _clean_html_response(self, html_text: str) -> str:
        """Removes newline characters from HTML response."""
        return html_text.replace('\n', '')

    def _filter_relevant_references(
        self, query: str, docs: List[Document]
    ) -> List[Document]:
        """
        Filters documents to only include those that are actually relevant to the query.
        Uses LLM to determine relevance based on document title, content preview, and metadata.
        """
        if not docs or len(docs) == 1:
            return docs

        # Build a summary of each document for relevance checking
        doc_summaries = []
        for i, doc in enumerate(docs):
            metadata = doc.metadata
            title = metadata.get("title", "Unknown Title")
            adr_number = metadata.get("adr_number", "Unknown")
            content_preview = doc.page_content[:200] if doc.page_content else ""

            technologies = []
            for key, value in metadata.items():
                if key.startswith("tech_") and value is True:
                    tech_name = key.replace("tech_", "").replace("_", " ").title()
                    technologies.append(tech_name)

            doc_summaries.append({
                "index": i,
                "title": title,
                "adr_number": adr_number,
                "content_preview": content_preview,
                "technologies": ", ".join(technologies) if technologies else "None specified"
            })

        # Create a prompt to determine which documents are relevant
        relevance_prompt = f"""
            You are a relevance filter for an Architecture Decision Records (ADRs) knowledge base system.

            User Query: "{query}"

            Below are summaries of documents that were retrieved. Your task is to identify which documents are ACTUALLY RELEVANT to the user's query.

            Document Summaries:
            """
        for summary in doc_summaries:
            relevance_prompt += f"""
            [{summary['index']}] ADR {summary['adr_number']}: {summary['title']}
            Technologies: {summary['technologies']}
            Content Preview: {summary['content_preview']}...
            """

        relevance_prompt += """
            Instructions:
            - A document is RELEVANT if it directly addresses the user's query topic, technologies, or use case
            - A document is NOT RELEVANT if it only matches on generic keywords but doesn't actually relate to the query
            - Be strict: only include documents that are clearly relevant to the query
            - Consider the document title, technologies, and content preview when making your decision

            Respond with ONLY a comma-separated list of document indices (0-based) that are relevant to the query.
            For example, if documents 0, 2, and 3 are relevant, respond with: 0,2,3
            If no documents are relevant, respond with: none
            """

        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            relevance_chain = (
                ChatPromptTemplate.from_template(relevance_prompt)
                | self.llm
                | StrOutputParser()
            )
            relevance_response = relevance_chain.invoke({}).strip().lower()

            # Parse the response
            if "none" in relevance_response or not relevance_response:
                return docs[:1]

            try:
                indices = [int(idx.strip()) for idx in relevance_response.split(",") if idx.strip().isdigit()]
                relevant_docs = [docs[i] for i in indices if 0 <= i < len(docs)]

                if not relevant_docs:
                    return docs[:1]

                return relevant_docs
            except (ValueError, IndexError) as e:
                print(f"Error parsing relevance filter response: {e}. Response: {relevance_response}")
                return docs

        except Exception as e:
            print(f"Error in relevance filtering: {e}. Returning all documents.")
            return docs

