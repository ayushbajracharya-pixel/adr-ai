# from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter

# from langchain.chains import RetrievalQA
# from langchain.prompts import PromptTemplate
from langchain.schema import Document
import pypdfium2 as pdfium
import tempfile
import os
import docx
import re
from typing import Dict, List, Optional


class ADRService:
    def __init__(self):
        # self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
        # self.llm = ChatOpenAI(
        # model="gpt-4", temperature=0.1, openai_api_key=os.getenv("OPENAI_API_KEY")
        # )
        # self.vectorstore = Chroma(
        # persist_directory="./chroma_db", embedding_function=self.embeddings
        # )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ". ", " "]
        )

    def extract_adr_metadata(self, text: str, filename: str) -> dict:
        """Extract metadata from ADR content - works with both markdown and flattened PDF/DOCX text"""
        metadata = {"filename": filename, "source": filename, "document_type": "ADR"}

        # Clean up text - handle both \n and actual newlines
        text_clean = text.replace("\\n", "\n")
        lines = text_clean.split("\n")

        # Extract title (first line or line containing ADR-XXXX)
        title = self.extract_title(text_clean, lines)
        if title:
            metadata["title"] = title
            # Extract ADR number
            adr_match = re.search(r"ADR-(\d+)", title)
            if adr_match:
                metadata["adr_number"] = adr_match.group(1)

        # Extract basic fields (works for both formats)
        metadata.update(self.extract_basic_fields(text_clean))

        # Extract decision makers
        decision_makers = self.extract_decision_makers(text_clean)
        if decision_makers:
            metadata["decision_makers"] = decision_makers

        # Extract requirements from context
        requirements = self.extract_requirements(text_clean)
        if requirements:
            metadata["requirements"] = requirements

        # Extract technologies mentioned
        metadata["mentioned_technologies"] = self.extract_technologies_from_text(
            text_clean
        )

        # Extract options considered
        options = self.extract_options(text_clean)
        if options:
            metadata["considered_options"] = options

        # Extract decision info
        decision_info = self.extract_decision_info(text_clean)
        if decision_info:
            metadata.update(decision_info)

        return metadata

    def extract_title(self, text: str, lines: List[str]) -> Optional[str]:
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

    def extract_basic_fields(self, text: str) -> Dict:
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

    def extract_decision_makers(self, text: str) -> List[str]:
        """Extract decision makers list"""
        decision_makers = []

        # Find the Decision Makers section
        patterns = [
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

    def extract_requirements(self, text: str) -> List[Dict]:
        """Extract requirements from context section"""
        requirements = []

        # Find context section (more flexible patterns)
        context_patterns = [
            r"Context\s*\n(.*?)(?=Considered Options|Options|Decision|\Z)",
            r"Context:\s*\n(.*?)(?=Considered Options|Options|Decision|\Z)",
            r"## Context\s*\n(.*?)(?=##|\Z)",
        ]

        context_text = None
        for pattern in context_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                context_text = match.group(1).strip()
                break

        if context_text:
            # Look for requirement patterns
            req_patterns = [
                r"([^:\n]+?):\s*([^\n]+(?:\n(?!\w+:)[^\n]*)*)",  # "High Throughput: description..."
                r"•\s*([^:\n]+?):\s*([^\n]+)",
                r"-\s*([^:\n]+?):\s*([^\n]+)",
            ]

            for pattern in req_patterns:
                matches = re.findall(pattern, context_text, re.MULTILINE)
                for match in matches:
                    req_name = match[0].strip()
                    req_desc = match[1].strip()

                    # Filter out non-requirement lines
                    if any(
                        keyword in req_name.lower()
                        for keyword in [
                            "throughput",
                            "latency",
                            "scalability",
                            "durability",
                            "fault",
                            "performance",
                            "availability",
                        ]
                    ):
                        requirements.append({"name": req_name, "description": req_desc})

        return requirements

    def extract_options(self, text: str) -> List[Dict]:
        """Extract considered options with pros/cons"""
        options = []

        # Find all "Option X:" sections
        option_pattern = (
            r"(Option \d+:.*?)\n(.*?)(?=Option \d+:|Decision\s*\n|Rationale|\Z)"
        )
        matches = re.findall(option_pattern, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            option_title = match[0].strip()
            option_content = match[1].strip()

            # Extract description
            desc_match = re.search(
                r"Description:\s*(.*?)(?=Pros|Cons|\n\n|\Z)",
                option_content,
                re.DOTALL | re.IGNORECASE,
            )
            description = desc_match.group(1).strip() if desc_match else ""

            # Extract pros
            pros = []
            pros_match = re.search(
                r"Pros\s*\n(.*?)(?=Cons|\n\n|Option|\Z)",
                option_content,
                re.DOTALL | re.IGNORECASE,
            )
            if pros_match:
                pros_text = pros_match.group(1)
                # Split by lines and clean
                for line in pros_text.split("\n"):
                    line_clean = line.strip()
                    if line_clean and not line_clean.lower().startswith(
                        ("cons", "option")
                    ):
                        # Remove bullet points
                        line_clean = re.sub(r"^[-•*]\s*", "", line_clean)
                        if (
                            line_clean and len(line_clean) > 10
                        ):  # Filter out short fragments
                            pros.append(line_clean)

            # Extract cons
            cons = []
            cons_match = re.search(
                r"Cons\s*\n(.*?)(?=Option|Decision|\n\n|\Z)",
                option_content,
                re.DOTALL | re.IGNORECASE,
            )
            if cons_match:
                cons_text = cons_match.group(1)
                for line in cons_text.split("\n"):
                    line_clean = line.strip()
                    if line_clean and not line_clean.lower().startswith(
                        ("option", "decision")
                    ):
                        line_clean = re.sub(r"^[-•*]\s*", "", line_clean)
                        if line_clean and len(line_clean) > 10:
                            cons.append(line_clean)

            options.append(
                {
                    "title": option_title,
                    "description": description,
                    "pros": pros,
                    "cons": cons,
                }
            )

        return options

    def extract_decision_info(self, text: str) -> Dict:
        """Extract final decision and rationale"""
        decision_info = {}

        # Extract chosen decision
        decision_patterns = [
            r"Decision\s*\n(.*?)(?=Rationale|Consequences|\Z)",
            r"## Decision\s*\n(.*?)(?=##|\Z)",
        ]

        for pattern in decision_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                decision_info["chosen_option"] = match.group(1).strip()
                break

        # Extract rationale
        rationale_patterns = [
            r"Rationale\s*\n(.*?)(?=Consequences|Mitigation|\Z)",
            r"## Rationale\s*\n(.*?)(?=##|\Z)",
        ]

        for pattern in rationale_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                decision_info["rationale"] = match.group(1).strip()
                break

        # Extract consequences
        consequences = {"positive": [], "negative": []}

        # Look for Positive/Negative sections
        positive_match = re.search(
            r"Positive\s*\n(.*?)(?=Negative|Mitigation|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if positive_match:
            pos_text = positive_match.group(1)
            for line in pos_text.split("\n"):
                line_clean = line.strip()
                if line_clean and not line_clean.lower().startswith(
                    ("negative", "mitigation")
                ):
                    line_clean = re.sub(r"^[-•*]\s*", "", line_clean)
                    if line_clean and len(line_clean) > 10:
                        consequences["positive"].append(line_clean)

        negative_match = re.search(
            r"Negative\s*\n(.*?)(?=Mitigation|Related|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if negative_match:
            neg_text = negative_match.group(1)
            for line in neg_text.split("\n"):
                line_clean = line.strip()
                if line_clean and not line_clean.lower().startswith(
                    ("mitigation", "related")
                ):
                    line_clean = re.sub(r"^[-•*]\s*", "", line_clean)
                    if line_clean and len(line_clean) > 10:
                        consequences["negative"].append(line_clean)

        if consequences["positive"] or consequences["negative"]:
            decision_info["consequences"] = consequences

        return decision_info

    def extract_technologies_from_text(self, text: str) -> List[str]:
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

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF using pypdfium2"""
        try:
            pdf = pdfium.PdfDocument(file_path)
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

    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from Word document"""
        try:
            doc = docx.Document(file_path)
            text_content = []

            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)

            return "\n".join(text_content)

        except Exception as e:
            raise Exception(f"Failed to extract Word document text: {str(e)}")

    def extract_text_from_file(self, file_path: str, filename: str) -> str:
        """Extract text based on file extension"""

        file_ext = filename.lower().split(".")[-1]

        if file_ext == "pdf":
            return self.extract_text_from_pdf(file_path)
        elif file_ext in ["docx", "doc"]:
            return self.extract_text_from_docx(file_path)
        elif file_ext in ["txt", "md"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            raise Exception(f"Unsupported file format: {file_ext}")

    async def process_adr(self, file):
        """Process uploaded ADR and add to knowledge base"""
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{file.filename.split('.')[-1]}"
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Extract text using pypdfium2 or other extractors
            text_content = self.extract_text_from_file(tmp_path, file.filename)

            # Extract metadata
            metadata = self.extract_adr_metadata(text_content, file.filename)

            # Create document with metadata
            document = Document(page_content=text_content, metadata=metadata)

            # Split and store
            splits = self.text_splitter.split_documents([document])

            # Ensure all chunks have metadata
            for split in splits:
                split.metadata.update(metadata)

            # doc_ids = self.vectorstore.add_documents(splits)

            return metadata

            # return {
            #     # "doc_id": doc_ids[0] if doc_ids else None,
            #     "filename": file.filename,
            #     "adr_number": metadata.get("adr_number"),
            #     "title": metadata.get("title"),
            #     "status": metadata.get("status"),
            #     "technologies_found": metadata.get("mentioned_technologies", []),
            # }

        finally:
            os.unlink(tmp_path)
