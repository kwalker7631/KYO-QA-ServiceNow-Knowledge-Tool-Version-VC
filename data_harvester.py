# data_harvester.py
# Author: Kenneth Walker
# Date: 2025-07-24
# Version: VC-9

import re

# This is the second version of the data harvesting module.
# Phase B: Pre-release - Version VC-9
# It now returns a status reason along with the found data.

# --- BUILT-IN PATTERNS ---
# In the future, this will be merged with the custom patterns from the manager.
PATTERNS = {
    "model": [
        r"\bTASKalfa\s*[\w-]+\b",
        r"\bECOSYS\s*[\w-]+\b",
        r"\bFS-\d+DN\b",
    ],
    "qa_number": [
        r"\bQA[-_]?[\w-]+\b",
        r"\bSB[-_]?\d+\b",
    ]
}

def harvest_all_data(text: str) -> dict:
    """
    Runs all defined patterns against the text and returns the results.

    Args:
        text: The full text content extracted from a PDF.

    Returns:
        A dictionary containing the list of found items and a reason for status.
        Example: {
            "found_items": [{"type": "model", "text": "ECOSYS M2540dn"}, ...],
            "status_reason": "Data found."
        }
    """
    found_items = []
    
    # Iterate through each category of patterns (e.g., "model", "qa_number")
    for item_type, regex_list in PATTERNS.items():
        # Iterate through each regex pattern in the category
        for pattern in regex_list:
            try:
                # Find all non-overlapping matches for the pattern in the text
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    found_text = match.group(0).strip()
                    
                    # Avoid adding duplicate entries
                    is_duplicate = any(
                        item['type'] == item_type and item['text'] == found_text
                        for item in found_items
                    )
                    if not is_duplicate:
                        found_items.append({"type": item_type, "text": found_text})
            except re.error as e:
                # This will catch any invalid regex patterns
                print(f"Regex error for pattern '{pattern}': {e}")

    status_reason = "Data found." if found_items else "No patterns matched."
    
    return {"found_items": found_items, "status_reason": status_reason}
