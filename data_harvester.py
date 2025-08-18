# data_harvester.py
# Author: Kenneth Walker
# Date: 2025-08-18 (Updated)
# Version: VA-1.3 (Added text cleaning)

import re
import importlib.util
from pathlib import Path

# --- Global Configuration ---
CUSTOM_PATTERNS_FILE = Path.cwd() / "custom_patterns.py"
IGNORED_PATTERNS_FILE = Path.cwd() / "ignored_patterns.py"

def get_all_patterns(load_custom: bool = True) -> dict:
    """
    Loads all regex patterns. It starts with built-in patterns and optionally
    merges them with user-defined patterns from an external file.
    """
    patterns = {
        "model": [
            r"\bTASKalfa\s*[\w-]+\b", r"\bECOSYS\s*[\w-]+\b",
            r"\bFS-C\d{4}DN\b", r"\bFS-\d{4,5}[ciDNw]*\b",
        ],
        "qa_number": [ r"\bQA[-_]?[\w-]+\b", r"\bSB[-_]?\d+\w*\b",],
        "author": [],  # Add custom patterns like r"Author:\s*([\w\s]+)"
        "topic": []    # Add custom patterns like r"\b(General|Desktop|Applications)\b"
    }
    if not load_custom: return patterns
    if CUSTOM_PATTERNS_FILE.exists():
        try:
            spec = importlib.util.spec_from_file_location("custom_patterns", CUSTOM_PATTERNS_FILE)
            custom_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(custom_module)
            for key in patterns:
                custom_list = getattr(custom_module, f"{key.upper()}_PATTERNS", [])
                patterns[key].extend([p for p in custom_list if p not in patterns[key]])
        except Exception as e:
            print(f"Warning: Could not load custom patterns. Error: {e}")
    return patterns

def load_ignored_patterns() -> dict:
    """Loads ignored regex patterns for each type from ignored_patterns.py."""
    ignored = {
        "model": [],
        "qa_number": [],
        "author": [],
        "topic": []
    }
    if IGNORED_PATTERNS_FILE.exists():
        try:
            spec = importlib.util.spec_from_file_location("ignored_patterns", IGNORED_PATTERNS_FILE)
            ignored_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ignored_module)
            for key in ignored:
                ignored[key] = getattr(ignored_module, f"IGNORED_{key.upper()}_PATTERNS", [])
        except Exception as e:
            print(f"Warning: Could not load ignored patterns. Error: {e}")
    return ignored

def harvest_all_data(text: str) -> dict:
    """
    Runs all defined patterns against a block of text, then filters out any
    matches that are on the ignore list for their type.
    """
    found_items = []
    all_patterns = get_all_patterns(load_custom=True)
    ignored_patterns = load_ignored_patterns()

    # --- Step 1: Find all potential matches ---
    for item_type, regex_list in all_patterns.items():
        for pattern in regex_list:
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # --- MODIFIED: Clean the found text ---
                    # Strip whitespace first, then remove unwanted leading/trailing characters
                    found_text = match.group(0).strip().strip(' ,/\\')
                    
                    is_duplicate = any(item['text'] == found_text for item in found_items)
                    if not is_duplicate and found_text: # Ensure not an empty string after stripping
                        display_type = item_type.replace("_", " ").capitalize()
                        if item_type == "qa_number":
                            display_type = "QA Number"
                        found_items.append({
                            "type": display_type,
                            "text": found_text,
                            "flagged": False  # Default state
                        })
            except re.error as e:
                print(f"Regex error in pattern '{pattern}': {e}")

    # --- Step 2: Mark and filter out ignored items ---
    final_items = []
    for item in found_items:
        is_ignored = False
        item_key = item['type'].replace(" ", "_").lower()  # e.g., "qa_number"
        for ignored_pattern in ignored_patterns.get(item_key, []):
            if re.search(ignored_pattern, item['text'], re.IGNORECASE):
                is_ignored = True
                break
        
        if is_ignored:
            item['flagged'] = True
            final_items.append(item)
        else:
            final_items.append(item)

    # The status should depend on finding VALID (not ignored) items.
    valid_items_found = any(not item['flagged'] for item in final_items)
    status_reason = "Data found and extracted." if valid_items_found else "No valid patterns found in document."
    if not valid_items_found and final_items:
        status_reason = "Found items were on the ignore list."

    return {"found_items": final_items, "status_reason": status_reason}