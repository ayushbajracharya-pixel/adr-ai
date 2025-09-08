from pydantic import BaseModel, Field
from typing import List, Optional


class QueryRequest(BaseModel):
    query: str


class Reference(BaseModel):
    filename: str
    content_preview: str


class QueryResponse(BaseModel):
    query: str
    answer: str
    references: List[Reference]
    # found_implementations: bool


class QueryIntent(BaseModel):
    """Structured representation of the user's project query intent."""

    technologies: List[str] = Field(
        ..., description="List of explicitly mentioned or inferred technologies."
    )
    requirements: List[str] = Field(
        ..., description="List of key technical or business requirements."
    )
    domain: Optional[str] = Field(
        None,
        description="The industry or domain of the project (e.g., healthcare, finance).",
    )
    compliance_needs: List[str] = Field(
        ..., description="Regulatory compliance needs like HIPAA, GDPR, or PCI-DSS."
    )
    use_case: Optional[str] = Field(
        None,
        description="The primary use case of the application (e.g., chat application, telemedicine).",
    )
