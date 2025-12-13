"""Query processing service for validating and processing queries."""
from typing import Dict, List, Optional, Any
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.domain.schemas.query import QueryIntent
from app.infrastructure.llm.chains.extraction_chain import ExtractionChain
from app.infrastructure.retrieval.retrieval_service import get_hybrid_retriever
from langchain_core.documents import Document


class QueryProcessor:
    """Handles query validation, intent extraction, and retrieval."""

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.extraction_chain = ExtractionChain()
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    def validate_query_quality(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Validates if a query is searchable and should trigger ADR retrieval.
        
        Returns:
            Dict with 'is_searchable' (bool) and 'reason' (str) if not searchable
        """
        query = query.strip()
        query_lower = query.lower().strip()

        # Quick heuristic checks
        if len(query) < 3:
            return {"is_searchable": False, "reason": "query_too_short"}

        # Check for common conversational fillers
        conversational_fillers = {
            "yeah", "yes", "yep", "yup", "ok", "okay", "okey", "sure", "cool",
            "thanks", "thank you", "thx", "nice", "great", "awesome", "perfect",
            "alright", "alrighty", "got it", "gotcha", "right", "correct",
            "understood", "i see", "i understand", "makes sense", "sounds good",
            "good", "fine", "okay then", "sure thing", "no problem", "np"
        }

        if query_lower in conversational_fillers:
            if query_lower in {"thanks", "thank you", "thx"} and conversation_history:
                for msg in reversed(conversation_history):
                    if msg.get("role") == "assistant":
                        return {"is_searchable": False, "reason": "thank_you_after_response"}
            return {"is_searchable": False, "reason": "conversational_filler"}

        # Check for meta-questions
        meta_question_patterns = [
            r"what (queries|questions|messages) (have|did) (i|you)",
            r"what (did|have) (i|you) (asked|said|queried)",
            r"show (me )?(my|the) (previous|past|earlier) (queries|questions|messages)",
            r"list (my|the) (queries|questions|messages)",
            r"what (have|did) (we|i) (talked|discussed)",
            r"what (is|are) (my|the) (conversation|chat) (history|log)",
            r"how (many|much) (queries|questions) (have|did) (i|you)",
            r"what (can|do) (you|i) (do|help)",
            r"what (are|is) (your|the) (capabilities|features|functions)",
            r"who (are|is) (you|this)",
            r"what (is|are) (this|you)",
            r"help (me|us)",
            r"what (should|can) (i|we) (ask|query)",
            r"how (do|does) (this|it|you) (work|function)",
        ]

        for pattern in meta_question_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return {"is_searchable": False, "reason": "meta_question"}

        # Check for greetings and closings
        greeting_patterns = [
            r"^(hi|hello|hey|greetings|good (morning|afternoon|evening))",
            r"^(bye|goodbye|see (you|ya)|farewell|take care)",
        ]

        for pattern in greeting_patterns:
            if re.match(pattern, query_lower):
                return {"is_searchable": False, "reason": "greeting_or_closing"}

        # Check word count
        words = query.split()
        if len(words) <= 1:
            return {"is_searchable": False, "reason": "insufficient_words"}

        # LLM-based classification
        try:
            history_context = ""
            if conversation_history:
                recent_messages = conversation_history[-settings.MAX_RECENT_MESSAGES:]
                history_context = "\n\nRecent conversation context:\n"
                for msg in recent_messages:
                    role = "User" if msg.get("role") == "user" else "Assistant"
                    content = msg.get("content", "")[: settings.MESSAGE_PREVIEW_LENGTH]
                    history_context += f"{role}: {content}\n"

            classification_prompt = f"""
            You are a query classifier for an Architecture Decision Records (ADRs) knowledge base system.
            
            Determine if the following user message is a SEARCHABLE query that should retrieve ADRs from the knowledge base, or if it's a CONVERSATIONAL message that should not trigger ADR retrieval.
            
            User message: "{query}"
            {history_context}
            
            Respond with ONLY one word: "searchable" or "conversational"
            
            Classify as "conversational" (DO NOT retrieve ADRs) if the message is:
            - An acknowledgment, agreement, or confirmation (yeah, ok, thanks, got it, etc.)
            - A greeting or closing (hi, hello, bye, goodbye, etc.)
            - A meta-question about the conversation itself
            - A question about the system's capabilities or how to use it
            - A request for help without a specific technical question
            - A simple statement without asking for information
            - Asking about conversation history, previous messages, or chat logs
            - Not requesting information about architecture, technology, or decisions
            - A follow-up acknowledgment to a previous response
            
            Classify as "searchable" (SHOULD retrieve ADRs) if the message is:
            - Asking a substantive question about architecture, technology, or design decisions
            - Requesting information, examples, or guidance about technical topics
            - Describing a use case, requirement, or problem that could match ADR content
            - Asking "what", "how", "why", "when", "where" questions about technical topics
            - Requesting comparisons, recommendations, or best practices
            - Any query that could reasonably match content in ADR documents
            """

            classification_chain = (
                ChatPromptTemplate.from_template(classification_prompt)
                | self.llm
                | StrOutputParser()
            )
            classification = classification_chain.invoke({}).strip().lower()

            if "conversational" in classification:
                return {"is_searchable": False, "reason": "llm_classified_conversational"}

        except Exception as e:
            print(f"Query classification failed: {e}. Allowing query to proceed.")

        return {"is_searchable": True, "reason": None}

    def extract_intent(self, query: str) -> QueryIntent:
        """
        Extract query intent using LLM chain.

        Args:
            query: The user's query

        Returns:
            QueryIntent object
        """
        try:
            intent_info = self.extraction_chain.invoke_intent_chain(query)
            print(f"Extracted Intent: {intent_info.model_dump()}")
            return intent_info
        except Exception as e:
            print(f"Intent extraction failed: {e}. Falling back to basic search.")
            return QueryIntent(
                technologies=[], requirements=[], compliance_needs=[]
            )

    def retrieve_documents(
        self, query: str, intent_info: QueryIntent
    ) -> List[Document]:
        """
        Retrieve documents using hybrid retrieval.

        Args:
            query: The user's query
            intent_info: Extracted query intent

        Returns:
            List of retrieved documents
        """
        intent_dict = intent_info.model_dump()
        retriever = get_hybrid_retriever(self.vector_store, intent_dict, query=query)
        retrieved_docs = retriever.invoke(query)
        return retrieved_docs

    def generate_conversational_response(
        self,
        query: str,
        reason: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a friendly conversational response for non-searchable queries.
        """
        query_lower = query.lower().strip()

        # Special handling for "thank you" after a response
        if reason == "thank_you_after_response" or (
            reason == "conversational_filler"
            and query_lower in {"thanks", "thank you", "thx"}
        ):
            if conversation_history:
                for msg in reversed(conversation_history):
                    if msg.get("role") == "assistant":
                        assistant_content = msg.get("content", "")
                        if (
                            len(assistant_content) > 50
                            and not assistant_content.startswith("<p>I'm here to help")
                        ):
                            return {
                                "query": query,
                                "response": "<p>You're welcome! Happy to help. Feel free to ask if you need anything else about architecture decisions. 🚀</p>",
                                "references": [],
                            }

        # Map reasons to appropriate responses
        response_templates = {
            "query_too_short": "<p>I'd be happy to help! Could you please provide more details about what you're looking for? 📌</p>",
            "conversational_filler": "<p>Got it! Feel free to ask me anything about architecture decisions or ADRs. 🚀</p>",
            "insufficient_words": "<p>I'd love to help! Could you provide a bit more detail about what you need? 💡</p>",
            "meta_question": "<p>I'm focused on helping you find information about architecture decisions and ADRs. Ask me questions about technologies, design patterns, or architectural choices, and I'll search through the ADR knowledge base for relevant information. 🔍</p>",
            "greeting_or_closing": "<p>Hello! I'm here to help you find information about architecture decisions and ADRs. What would you like to know? 🚀</p>",
            "llm_classified_conversational": "<p>I'm here to help with questions about architecture decisions and ADRs. What would you like to know? 🔍</p>",
        }

        default_response = "<p>I'm here to help! What would you like to know about architecture decisions? 🚀</p>"
        response_html = response_templates.get(reason, default_response)

        return {
            "query": query,
            "response": response_html,
            "references": [],
        }

