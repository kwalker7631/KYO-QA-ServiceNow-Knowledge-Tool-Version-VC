# custom_patterns.py
# Last updated: 2025-08-18 01:59:23

MODEL_PATTERNS = [
    r'\bKM\-\d+\b',
    r'\bVi\d+\b',
    r'\bkM\-\d+\b',
]

QA_NUMBER_PATTERNS = [
    r'\bM\d{3}\b',
]


MODEL_PATTERNS.append(r'\bM\d+idnf\b')

MODEL_PATTERNS.append(r'\bPF\~\d{3}\b')

MODEL_PATTERNS.append(r'\bPZ\-\d{3}\b')

MODEL_PATTERNS.append(r'\bKM\-\d{4}w\b')

MODEL_PATTERNS.append(r'\bP\d{4}cdn\b')
