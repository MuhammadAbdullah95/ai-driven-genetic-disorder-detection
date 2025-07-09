import json


def extract_json_from_markdown(markdown_string):
    """
    Extracts a JSON string from a Markdown code block, ignoring any leading text.

    Args:
        markdown_string (str): The string potentially containing a Markdown JSON code block.

    Returns:
        str: The extracted pure JSON string, or None if no valid JSON code block is found.
    """
    # Define the possible start delimiters for the JSON code block
    # We check for '```json' first, then fallback to generic '```'
    start_delimiters = ["```json", "```"]
    start_index = -1
    chosen_delimiter_len = 0

    for delim in start_delimiters:
        start_index = markdown_string.find(delim)
        if start_index != -1:
            chosen_delimiter_len = len(delim)
            break # Found a delimiter, stop searching

    if start_index == -1:
        return None # No code block start delimiter found

    # Adjust start_index to point to the beginning of the JSON data
    start_index += chosen_delimiter_len

    # Find the end of the JSON content, starting the search *after* the start delimiter
    end_delimiter = "```"
    end_index = markdown_string.find(end_delimiter, start_index)
    if end_index == -1:
        return None # End delimiter not found after start

    # Extract the substring containing the pure JSON
    json_string = markdown_string[start_index:end_index].strip()

    return json_string
