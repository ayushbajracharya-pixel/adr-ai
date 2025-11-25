from pydantic import BaseModel, Field
from typing import List, Optional


class QueryRequest(BaseModel):
    query: str


class Reference(BaseModel):
    filename: str
    adr_number: str
    title: str
    status: str
    author: str
    date: str
    source: str
    public_url: str
    s3_uri: str
    content_preview: Optional[str] = None


class QueryResponse(BaseModel):
    query: str
    response: str
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


class ADRMetadata(BaseModel):
    adr_number: str = Field(description="The ADR ID, e.g., ADR-0001")
    title: str = Field(description="The title of the ADR document.")
    status: str = Field(
        description="The status of the ADR, e.g., 'Accepted', 'Superseded'."
    )
    date: str = Field(description="The date the ADR was created.")
    author: str = Field(description="The author of the ADR.")
    decision_makers: list[str] = Field(
        description="A list of names of the decision makers. Normally, persons who have reviewed and/or approved the ADR."
    )
    context: str = Field(
        description="A summary of the project context and requirements."
    )
    considered_options: list[str] = Field(
        description="A list of the options that were considered."
    )
    decision: str = Field(description="The final decision that was made.")
    rationale: str = Field(description="The reasoning behind the decision.")
    tech: list[str] = Field(
        description="A list of technologies mentioned in the ADR. Technologies includes programming languages, framework, libraries and paradigms."
    )
    # consequences_positive: list[str] = Field(
    #     description="A list of the positive consequences of the decision."
    # )
    # consequences_negative: list[str] = Field(
    #     description="A list of the negative consequences of the decision."
    # )
