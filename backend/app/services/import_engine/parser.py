"""
CSV Parser — Stage 3 of the import pipeline.

Reads and parses the uploaded CSV file into a list of raw row dictionaries.
Handles structural validation: expected columns, empty files, broken structure.
"""
import csv
import io
from typing import List, Dict, Tuple

EXPECTED_COLUMNS = [
    "date", "description", "paid_by", "amount", "currency",
    "split_type", "split_with", "split_details", "notes"
]


def parse_csv(file_content: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Parse CSV content into a list of row dictionaries.
    
    Returns:
        (rows, errors) — rows is a list of dicts, errors is a list of structural issues
    """
    errors = []
    rows = []

    if not file_content or not file_content.strip():
        errors.append("CSV file is empty")
        return rows, errors

    try:
        reader = csv.DictReader(io.StringIO(file_content))
    except Exception as e:
        errors.append(f"Failed to parse CSV structure: {str(e)}")
        return rows, errors

    # Validate columns
    if reader.fieldnames is None:
        errors.append("CSV file has no header row")
        return rows, errors

    actual_cols = [c.strip().lower() for c in reader.fieldnames]
    missing_cols = [c for c in EXPECTED_COLUMNS if c not in actual_cols]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        return rows, errors

    # Parse rows
    for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        cleaned = {}
        for key, value in row.items():
            cleaned[key.strip().lower()] = (value or "").strip()
        cleaned["_row_number"] = i
        rows.append(cleaned)

    if not rows:
        errors.append("CSV file contains no data rows")

    return rows, errors
