from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from app.models.schemas import ADRMetadata, QueryIntent


class ExtractionChain:
    def __init__(self, model_name="gpt-4.1-nano", temperature=0):
        self.model = ChatOpenAI(model=model_name, temperature=temperature)

        self.intent_chain = self._get_intent_extraction_chain()
        self.metadata_chain = self._get_metadata_extraction_chain()

    def invoke_intent_chain(self, query: str) -> QueryIntent:
        return self.intent_chain.invoke({"query": query})

    def invoke_metadata_chain(self, text: str) -> ADRMetadata:
        return self.metadata_chain.invoke(
            {
                "text": text,
            }
        )

    def _get_intent_extraction_chain(self):
        """Builds and returns a LangChain chain for extracting query intent."""
        parser = PydanticOutputParser(pydantic_object=QueryIntent)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert project analyst. Analyze the user's project query and extract the key intent into a JSON object. 
                    Return the output only in the specified JSON format. If a category is not mentioned, return an empty list or null as appropriate. 
                    The user's query may contain implied technologies and requirements, so infer them where possible.\n\n{format_instructions}""",
                ),
                ("human", "Analyze this project query:\n\n{query}"),
            ]
        ).partial(format_instructions=parser.get_format_instructions())

        return prompt | self.model | parser

    def _get_metadata_extraction_chain(self):
        """Builds and returns a LangChain chain for extracting metadata."""
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
