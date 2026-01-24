"""CSV parsing service with encoding detection."""

import csv
import io
import re
from dataclasses import dataclass


@dataclass
class ParsedLead:
    """Parsed lead from CSV."""

    phone_number: str
    name: str | None = None
    company: str | None = None
    email: str | None = None
    notes: str | None = None


@dataclass
class CSVParseResult:
    """Result of CSV parsing."""

    leads: list[ParsedLead]
    errors: list[dict[str, str]]


E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")


def detect_encoding(content: bytes) -> str:
    """Detect encoding of CSV content."""
    # Try UTF-8 first
    try:
        content.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # Try Shift_JIS (common in Japan)
    try:
        content.decode("shift_jis")
        return "shift_jis"
    except UnicodeDecodeError:
        pass

    # Try CP932 (Windows Japanese)
    try:
        content.decode("cp932")
        return "cp932"
    except UnicodeDecodeError:
        pass

    # Default to UTF-8 with error handling
    return "utf-8"


def parse_csv(content: bytes) -> CSVParseResult:
    """
    Parse CSV content with automatic encoding detection.

    Args:
        content: Raw CSV bytes

    Returns:
        CSVParseResult with parsed leads and any errors
    """
    if not content or not content.strip():
        raise ValueError("Empty CSV file")

    encoding = detect_encoding(content)
    text = content.decode(encoding, errors="replace")

    # Parse CSV
    reader = csv.DictReader(io.StringIO(text))

    # Check for required column
    if reader.fieldnames is None:
        raise ValueError("Invalid CSV format")

    fieldnames_lower = [f.lower().strip() for f in reader.fieldnames]
    if "phone_number" not in fieldnames_lower:
        raise ValueError("Missing required column: phone_number")

    # Map column names (case-insensitive)
    column_map = {f.lower().strip(): f for f in reader.fieldnames}

    leads: list[ParsedLead] = []
    errors: list[dict[str, str]] = []

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
        phone_key = column_map.get("phone_number")
        phone = row.get(phone_key, "").strip() if phone_key else ""

        # Validate phone number
        if not phone:
            errors.append({"row": str(row_num), "error": "Empty phone number"})
            continue

        if not E164_PATTERN.match(phone):
            errors.append({"row": str(row_num), "error": f"Invalid phone format: {phone}"})
            continue

        # Extract optional fields
        name = row.get(column_map.get("name", ""), "").strip() or None
        company = row.get(column_map.get("company", ""), "").strip() or None
        email = row.get(column_map.get("email", ""), "").strip() or None
        notes = row.get(column_map.get("notes", ""), "").strip() or None

        leads.append(
            ParsedLead(
                phone_number=phone,
                name=name,
                company=company,
                email=email,
                notes=notes,
            )
        )

    return CSVParseResult(leads=leads, errors=errors)
