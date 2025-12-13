"""Metadata extraction service."""
from typing import Dict, Any
from app.infrastructure.llm.chains.extraction_chain import ExtractionChain
from app.utils.text_processing import one_hot_encode_lists_in_dict


class MetadataExtractor:
    """Handles metadata extraction and transformation."""

    def __init__(self):
        self.extraction_chain = ExtractionChain()

    def extract_and_transform_metadata(
        self, text_content: str, file_name: str, s3_uri: str, public_url: str
    ) -> Dict[str, Any]:
        """
        Extract metadata from text and transform it for storage.

        Args:
            text_content: The text content of the document
            file_name: Name of the file
            s3_uri: S3 URI of the uploaded file
            public_url: Public URL of the file

        Returns:
            Transformed metadata dictionary
        """
        extracted_metadata = self.extraction_chain.invoke_metadata_chain(text_content)
        extracted_metadata_dict = extracted_metadata.model_dump()
        extracted_metadata_dict["filename"] = file_name
        extracted_metadata_dict["source"] = file_name
        extracted_metadata_dict["s3_uri"] = s3_uri
        extracted_metadata_dict["public_url"] = public_url

        transformed_metadata = one_hot_encode_lists_in_dict(extracted_metadata_dict)
        return transformed_metadata

