"""
Text cleaning utilities shared across extractors.
"""
import re
import unicodedata


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into single space/newline."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_control_characters(text: str) -> str:
    """Remove non-printable / control characters while preserving Arabic."""
    return "".join(
        ch for ch in text
        if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t")
    )


def clean_text(text: str) -> str:
    """Full pipeline: remove control chars then normalize whitespace."""
    text = remove_control_characters(text)
    text = normalize_whitespace(text)
    return text
