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


def one_hot_encode_lists_in_dict(data: dict) -> dict:
    """
    Dynamically transforms list-based fields in a dictionary into one-hot encoded boolean fields.
    For each field, it checks if the value is a list. If so, it
    creates a new boolean key for each item and removes the original list.
    """
    new_data = {}

    for key, value in data.items():
        if isinstance(value, list):
            for item in value:
                # Sanitize the item string to create a valid, lowercase key.
                if isinstance(item, str):
                    sanitized_item = re.sub(r"\W+", "_", item).strip("_").lower()
                    new_key = f"{key}_{sanitized_item}"
                    new_data[new_key] = True
        else:
            # If the value is not a list, just copy the key-value pair as is.
            new_data[key] = value

    return new_data
