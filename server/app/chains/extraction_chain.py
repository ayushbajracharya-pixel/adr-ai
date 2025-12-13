from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from typing import Dict, Any

from app.models.schemas import ADRMetadata, QueryIntent
from app.config.settings import settings
from datetime import datetime


class ExtractionChain:
    def __init__(
        self,
        model_name: str = settings.EXTRACTION_MODEL_NAME,
        temperature: float = settings.EXTRACTION_TEMPERATURE,
    ) -> None:
        """
        Initialize the ExtractionChain with configurable model and temperature.

        Args:
            model_name: The OpenAI model name to use for extraction
            temperature: The temperature setting for the LLM (0.0 for deterministic)
        """
        self.model = ChatOpenAI(
            model=model_name,
            temperature=temperature,
        )

        self.intent_chain: Runnable[Dict[str, str], QueryIntent] = (
            self._get_intent_extraction_chain()
        )
        self.metadata_chain: Runnable[Dict[str, str], ADRMetadata] = (
            self._get_metadata_extraction_chain()
        )

    def invoke_intent_chain(self, query: str) -> QueryIntent:
        """
        Extract query intent from a user query.

        Args:
            query: The user's query string

        Returns:
            QueryIntent object containing extracted technologies, requirements, etc.
        """
        intent = self.intent_chain.invoke({"query": query})
        
        # Post-process date ranges for relative dates
        if intent.date_from and "last year" in query.lower():
            current_year = datetime.now().year
            intent.date_from = str(current_year - 1)
            intent.date_to = str(current_year - 1)
        elif intent.date_from and "this year" in query.lower():
            current_year = datetime.now().year
            intent.date_from = str(current_year)
            intent.date_to = str(current_year)
        
        return intent

    def invoke_metadata_chain(self, text: str) -> ADRMetadata:
        """
        Extract metadata from ADR document text.

        Args:
            text: The full text content of an ADR document

        Returns:
            ADRMetadata object containing extracted metadata
        """
        return self.metadata_chain.invoke({"text": text})

    def _get_intent_extraction_chain(
        self,
    ) -> Runnable[Dict[str, str], QueryIntent]:
        """
        Builds and returns a LangChain chain for extracting query intent.

        Returns:
            A Runnable chain that takes a query dict and returns QueryIntent
        """
        parser = PydanticOutputParser(pydantic_object=QueryIntent)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert project analyst. Analyze the user's query and extract the key intent into a JSON object.
                    
                    Extract the following information:
                    - Technologies: List of technologies mentioned or inferred (e.g., "kafka", "PostgreSQL", "React")
                    - Requirements: Technical or business requirements mentioned
                    - Domain: Industry or domain (e.g., "healthcare", "finance", "e-commerce")
                    - Compliance needs: Regulatory requirements (e.g., "HIPAA", "GDPR", "PCI-DSS")
                    - Use case: Primary use case of the application
                    
                    Metadata filters (extract if mentioned):
                    - Author: Author name (e.g., "Mr X", "John Doe", "Jane Smith")
                    - Status: ADR status (e.g., "Accepted", "Proposed", "Superseded", "Rejected")
                    - Date ranges: Extract date_from and date_to from phrases like:
                      * "in 2024" → date_from: "2024", date_to: "2024"
                      * "last year" → date_from: "2023", date_to: "2023" (adjust based on current year)
                      * "between 2023 and 2024" → date_from: "2023", date_to: "2024"
                      * "after 2023" → date_from: "2023", date_to: null
                      * "before 2024" → date_from: null, date_to: "2024"
                      * "in the last year" → calculate from current date
                    - Query type: Determine if this is a "list", "filter", "semantic", or "hybrid" query
                    
                    Examples:
                    - "What ADRs do we have?" → query_type: "list"
                    - "List accepted ADRs" → query_type: "list", status: "Accepted"
                    - "ADRs by author John Doe" → query_type: "filter", author: "John Doe"
                    - "Have you considered kafka in past projects in 2024?" → query_type: "hybrid", technologies: ["kafka"], date_from: "2024", date_to: "2024"
                    - "What database should we use?" → query_type: "semantic"
                    
                    Return the output only in the specified JSON format. If a category is not mentioned, return an empty list or null as appropriate.
                    The user's query may contain implied technologies and requirements, so infer them where possible.\n\n{format_instructions}""",
                ),
                ("human", "Analyze this query:\n\n{query}"),
            ]
        ).partial(format_instructions=parser.get_format_instructions())

        return prompt | self.model | parser

    def _get_metadata_extraction_chain(
        self,
    ) -> Runnable[Dict[str, str], ADRMetadata]:
        """
        Builds and returns a LangChain chain for extracting metadata.

        Returns:
            A Runnable chain that takes a text dict and returns ADRMetadata
        """
        parser = JsonOutputParser(pydantic_object=ADRMetadata)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert at extracting architectural decision records (ADR) metadata. Extract the following information from the provided text and return it as a JSON object.",
                ),
                (
                    "user",
                    "Extract the metadata from this ADR:\n\n{text}\n\n{format_instructions}",
                ),
            ]
        ).partial(format_instructions=parser.get_format_instructions())

        return prompt | self.model | parser
