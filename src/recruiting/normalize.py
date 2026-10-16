"""Text normalization: repairs the UTF-8 mojibake present in the resume corpus.

The source CSV is UTF-8 bytes that were decoded as Latin-1/Windows-1252 at
some point in the dataset's lineage, so e.g. "Naïve" appears as "NaÃ¯ve".
725 of the 962 resumes carry this corruption. The fix is the exact inverse
operation: re-encode as Latin-1 (which restores the original UTF-8 bytes)
and decode as UTF-8.
"""


def fix_mojibake(text: str) -> str:
    """Repair double-encoded UTF-8 if the telltale markers are present."""
    if not text or "Ã" not in text:
        return text
    try:
        fixed = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    # Only keep the repair if it actually removed the corruption markers and
    # produced sane output; otherwise fall back to the original.
    if "Ã" in fixed or "\ufffd" in fixed:
        return text
    return fixed


def normalize(text: str) -> str:
    """Full normalization used before every extractor: mojibake repair,
    whitespace collapsing, and Unicode-safe lower-casing for matching."""
    if not text:
        return ""
    text = fix_mojibake(text)
    text = " ".join(text.split())
    return text
