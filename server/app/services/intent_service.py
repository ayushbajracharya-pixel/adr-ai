# app/services/intent_service.py

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.models.schemas import QueryIntent


def get_intent_extraction_chain():
    """Builds and returns a LangChain chain for extracting query intent."""
    llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0)
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

    return prompt | llm | parser
