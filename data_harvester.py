# data_harvester.py
# Author: Kenneth Walker
# Date: 2025-08-15
# Version: VA-1.1 (Final Alpha)

import re
import importlib.util
from pathlib import Path

# --- Global Configuration ---
CUSTOM_PATTERNS_FILE = Path.cwd() / "custom_patterns.py"
# --- NEW: File to store ignored/flagged patterns ---
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
        "qa_number": [ r"\bQA[-_]?[\w-]+\b", r"\bSB[-_]?\d+\w*\b",]
    }
    if not load_custom: return patterns
    if CUSTOM_PATTERNS_FILE.exists():
        try:
            spec = importlib.util.spec_from_file_location("custom_patterns", CUSTOM_PATTERNS_FILE)
            custom_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(custom_module)
            custom_model = getattr(custom_module, "MODEL_PATTERNS", [])
            custom_qa = getattr(custom_module, "QA_NUMBER_PATTERNS", [])
            patterns["model"].extend([p for p in custom_model if p not in patterns["model"]])
            patterns["qa_number"].extend([p for p in custom_qa if p not in patterns["qa_number"]])
        except Exception as e:
            print(f"Warning: Could not load custom patterns. Error: {e}")
    return patterns

def load_ignored_patterns() -> list:
    """Loads a simple list of regex patterns to ignore from the ignored_patterns.py file."""
    ignored = []
    if IGNORED_PATTERNS_FILE.exists():
        try:
            spec = importlib.util.spec_from_file_location("ignored_patterns", IGNORED_PATTERNS_FILE)
            ignored_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ignored_module)
            ignored = getattr(ignored_module, "IGNORED_MODEL_PATTERNS", [])
        except Exception as e:
            print(f"Warning: Could not load ignored patterns. Error: {e}")
    return ignored

def harvest_all_data(text: str) -> dict:
    """
    Runs all defined patterns against a block of text, then filters out any
    matches that are on the ignore list.
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
                    found_text = match.group(0).strip()
                    is_duplicate = any(item['text'] == found_text for item in found_items)
                    if not is_duplicate:
                        found_items.append({
                            "type": item_type.replace("_", " ").capitalize(),
                            "text": found_text,
                            "flagged": False # Default state
                        })
            except re.error as e:
                print(f"Regex error in pattern '{pattern}': {e}")

    # --- Step 2: Mark and filter out ignored items ---
    final_items = []
    for item in found_items:
        is_ignored = False
        # Only check models against the ignore list for now
        if item['type'] == 'Model':
            for ignored_pattern in ignored_patterns:
                if re.search(ignored_pattern, item['text'], re.IGNORECASE):
                    is_ignored = True
                    break # Found a match in the ignore list, no need to check further
        
        if is_ignored:
            # If it's ignored, we still want to know it was found, but flag it.
            # The main app will use this flag for highlighting.
            item['flagged'] = True
            final_items.append(item)
        else:
            final_items.append(item)

    # The status should depend on finding VALID (not ignored) items.
    valid_items_found = any(not item['flagged'] for item in final_items)
    status_reason = "Data found and extracted." if valid_items_found else "No valid patterns found in document."
    if not valid_items_found and final_items:
        status_reason = "Found models were on the ignore list."

    return {"found_items": final_items, "status_reason": status_reason}
