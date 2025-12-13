import re


def clean_text_from_bullets(text):
    """
    Removes common bullet points and list markers using regular expressions.
    """
    # This regex pattern matches:
    # 1. Start of line followed by common list markers (•, -, *, 1., a), plus optional space
    # 2. Tabs or multiple spaces
    # 3. Newlines
    # You can add more specific patterns to the list if needed.

    pattern = r"^\s*[\u2022\u2023\u25b6\u25cf\u25aa•*-]\s*|^\s*[0-9]+\.\s*|^\s*[a-z]\.\s*|[\t\r\n]+"

    # Use re.sub to find and replace all matches with a single space
    cleaned_text = re.sub(pattern, " ", text, flags=re.MULTILINE)

    # Clean up any extra spaces
    return re.sub(r"\s+", " ", cleaned_text).strip()


def normalize_technology_name(tech: str) -> str:
    """
    Normalize a technology name to match the format used in one-hot encoding.
    This ensures consistent filtering between storage and query.
    
    Examples:
        "Vue.js" -> "vue_js"
        "C++" -> "c"
        "ASP.NET" -> "asp_net"
        "React" -> "react"
    
    Args:
        tech: Technology name string
        
    Returns:
        Normalized technology name (lowercase, non-word chars replaced with underscores)
    """
    if not isinstance(tech, str):
        return str(tech).lower()
    return re.sub(r"\W+", "_", tech).strip("_").lower()


def normalize_status(status: str) -> str:
    """
    Normalize ADR status to ensure consistent filtering between storage and query.
    Standardizes common status values to title case.
    
    Examples:
        "accepted" -> "Accepted"
        "ACCEPTED" -> "Accepted"
        "proposed" -> "Proposed"
        "superseded" -> "Superseded"
    
    Args:
        status: Status string
        
    Returns:
        Normalized status (title case for standard values)
    """
    if not isinstance(status, str):
        return str(status)
    
    status_lower = status.strip().lower()
    
    # Standard status values - normalize to title case
    standard_statuses = {
        "accepted": "Accepted",
        "proposed": "Proposed",
        "superseded": "Superseded",
        "rejected": "Rejected",
        "deprecated": "Deprecated",
        "withdrawn": "Withdrawn",
    }
    
    # Return standard status if found, otherwise return title case
    return standard_statuses.get(status_lower, status.strip().title())


def normalize_domain(domain: str) -> str:
    """
    Normalize domain/industry name to ensure consistent filtering between storage and query.
    Converts to lowercase for case-insensitive matching.
    
    Examples:
        "Healthcare" -> "healthcare"
        "E-Commerce" -> "e-commerce"
        "FINANCE" -> "finance"
    
    Args:
        domain: Domain/industry string
        
    Returns:
        Normalized domain (lowercase)
    """
    if not isinstance(domain, str):
        return str(domain).lower()
    return domain.strip().lower()


def one_hot_encode_lists_in_dict(data: dict) -> dict:
    """
    Dynamically transforms list-based fields in a dictionary into one-hot encoded boolean fields.
    For each field, it checks if the value is a list. If so, it
    creates a new boolean key for each item and removes the original list.
    Also normalizes domain and status fields for consistent filtering.
    """
    new_data = {}

    for key, value in data.items():
        if isinstance(value, list):
            for item in value:
                # Sanitize the item string to create a valid, lowercase key.
                if isinstance(item, str):
                    sanitized_item = normalize_technology_name(item)
                    new_key = f"{key}_{sanitized_item}"
                    new_data[new_key] = True
        else:
            # Normalize domain and status fields for consistent filtering
            if key == "domain" and isinstance(value, str):
                new_data[key] = normalize_domain(value)
            elif key == "status" and isinstance(value, str):
                new_data[key] = normalize_status(value)
            else:
                # If the value is not a list, just copy the key-value pair as is.
                new_data[key] = value

    return new_data
