"""
Row Normalizer — Stage 4 of the import pipeline.

Takes raw row data and normalizes:
- Dates: multiple formats → YYYY-MM-DD
- Amounts: strip commas, whitespace, currency symbols → Decimal
- Names: normalize casing, strip whitespace
- Currency: default empty to INR
- Split type: normalize to enum values
"""
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Optional


# --- Date Normalization ---

def normalize_date(raw_date: str) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Attempt to parse a date string in multiple formats.
    
    Returns:
        (normalized_date_str, warning_message, is_ambiguous)
    """
    if not raw_date:
        return None, "Date is empty", False

    raw_date = raw_date.strip()

    # Format 1: YYYY-MM-DD (ISO)
    try:
        d = datetime.strptime(raw_date, "%Y-%m-%d")
        return d.strftime("%Y-%m-%d"), None, False
    except ValueError:
        pass

    # Format 2: DD/MM/YYYY
    try:
        d = datetime.strptime(raw_date, "%d/%m/%Y")
        # Check for ambiguity: if both day and month ≤ 12, the format is ambiguous
        parts = raw_date.split("/")
        day_val, month_val = int(parts[0]), int(parts[1])
        is_ambiguous = day_val <= 12 and month_val <= 12 and day_val != month_val
        return d.strftime("%Y-%m-%d"), None, is_ambiguous
    except ValueError:
        pass

    # Format 3: Mon DD (e.g., "Mar 14") — assume current year context (2026)
    try:
        d = datetime.strptime(raw_date + " 2026", "%b %d %Y")
        return d.strftime("%Y-%m-%d"), f"Year inferred as 2026 for date '{raw_date}'", False
    except ValueError:
        pass

    # Format 4: MM/DD/YYYY (US format fallback)
    try:
        d = datetime.strptime(raw_date, "%m/%d/%Y")
        return d.strftime("%Y-%m-%d"), None, False
    except ValueError:
        pass

    return None, f"Could not parse date: '{raw_date}'", False


# --- Amount Normalization ---

def normalize_amount(raw_amount: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Normalize an amount string to a Decimal value.
    
    Handles: commas, whitespace, currency symbols, quoted values.
    Returns: (decimal_value, warning_message)
    """
    if not raw_amount:
        return None, "Amount is empty"

    cleaned = raw_amount.strip()
    # Remove currency symbols
    cleaned = cleaned.replace("₹", "").replace("$", "").replace("€", "")
    # Remove commas (thousands separator)
    cleaned = cleaned.replace(",", "")
    # Remove remaining whitespace
    cleaned = cleaned.strip()

    if not cleaned:
        return None, "Amount is empty after cleaning"

    # Check for letter 'O' instead of '0'
    if re.search(r'[A-Za-z]', cleaned):
        # Try to replace common OCR-like errors
        attempted = cleaned.replace('O', '0').replace('o', '0').replace('l', '1')
        try:
            val = Decimal(attempted)
            return val, f"Amount contained letters, auto-corrected '{raw_amount}' → '{attempted}'"
        except InvalidOperation:
            return None, f"Amount contains non-numeric characters: '{raw_amount}'"

    try:
        val = Decimal(cleaned)
        warning = None
        if cleaned != raw_amount.strip():
            warning = f"Amount normalized: '{raw_amount}' → '{cleaned}'"
        return val, warning
    except InvalidOperation:
        return None, f"Invalid numeric format: '{raw_amount}'"


# --- Name Normalization ---

def normalize_name(raw_name: str) -> Tuple[str, Optional[str]]:
    """
    Normalize a person's name: trim, title-case, handle variants.
    Returns: (normalized_name, warning)
    """
    if not raw_name:
        return "", "Name is empty"

    cleaned = raw_name.strip()
    if not cleaned:
        return "", "Name is empty"

    warning = None
    original = cleaned

    # Title-case the name
    cleaned = cleaned.title()

    if cleaned != original:
        warning = f"Name normalized: '{original}' → '{cleaned}'"

    return cleaned, warning


# --- Name Mapping ---

# Known name variants to canonical names
NAME_VARIANTS = {
    "priya s": "Priya",
    "rohan ": "Rohan",  # trailing space
}


def resolve_name(raw_name: str, known_users: List[str]) -> Tuple[str, Optional[str], bool]:
    """
    Resolve a raw name to a known user.
    
    Returns:
        (resolved_name, warning, needs_user_review)
    """
    normalized, norm_warning = normalize_name(raw_name)
    lower = normalized.lower().strip()

    # Check direct match (case-insensitive)
    for known in known_users:
        if known.lower() == lower:
            return known, norm_warning, False

    # Check known variants
    if lower in NAME_VARIANTS:
        mapped_to = NAME_VARIANTS[lower]
        return mapped_to, f"Name variant mapped: '{raw_name}' → '{mapped_to}'", False

    # Check partial match
    for known in known_users:
        if lower.startswith(known.lower()) or known.lower().startswith(lower):
            return known, f"Name fuzzy-matched: '{raw_name}' → '{known}' (needs confirmation)", True

    # Unknown user
    return normalized, None, False


# --- Currency Normalization ---

def normalize_currency(raw_currency: str) -> Tuple[str, Optional[str]]:
    """Normalize currency code. Default empty to INR."""
    if not raw_currency or not raw_currency.strip():
        return "INR", "Currency was empty, defaulted to INR"

    upper = raw_currency.strip().upper()
    if upper in ("INR", "USD"):
        return upper, None

    return upper, f"Unsupported currency: '{raw_currency}'"


# --- Split Type Normalization ---

def normalize_split_type(raw_split_type: str) -> Tuple[Optional[str], Optional[str]]:
    """Normalize split type to one of: equal, unequal, percentage, share."""
    if not raw_split_type or not raw_split_type.strip():
        return None, "Split type is empty"

    lower = raw_split_type.strip().lower()

    mapping = {
        "equal": "equal",
        "unequal": "unequal",
        "exact": "unequal",
        "percentage": "percentage",
        "percent": "percentage",
        "share": "share",
        "shares": "share",
        "unit": "share",
    }

    if lower in mapping:
        return mapping[lower], None

    return None, f"Unsupported split type: '{raw_split_type}'"


# --- Split Details Parser ---

def parse_split_details(raw_details: str, split_type: str) -> Tuple[List[Dict], Optional[str]]:
    """
    Parse split details string like "Aisha 30%; Rohan 30%; Priya 30%; Meera 20%"
    or "Rohan 700; Priya 400; Meera 400"
    or "Aisha 1; Rohan 2; Priya 1; Dev 2"
    
    Returns: (list of {name, value}, warning)
    """
    if not raw_details or not raw_details.strip():
        return [], None

    parts = [p.strip() for p in raw_details.split(";")]
    result = []
    warning = None

    for part in parts:
        if not part:
            continue
        # Match pattern: "Name Value[%]"
        match = re.match(r'^(.+?)\s+([\d.]+)(%?)$', part.strip())
        if match:
            name = match.group(1).strip()
            value = match.group(2)
            is_pct = match.group(3) == '%'
            result.append({
                "name": name,
                "value": float(value),
                "is_percentage": is_pct,
            })
        else:
            warning = f"Could not parse split detail: '{part}'"

    return result, warning


# --- Full Row Normalizer ---

def normalize_row(raw_row: Dict[str, str], known_users: List[str]) -> Tuple[Dict, List[Dict]]:
    """
    Normalize an entire raw CSV row.
    
    Returns:
        (normalized_data, list_of_anomalies)
        Each anomaly is: {type, severity, description, auto_resolved, auto_resolution, requires_user_action}
    """
    anomalies = []
    normalized = {"_row_number": raw_row.get("_row_number")}

    # Date
    norm_date, date_warning, date_ambiguous = normalize_date(raw_row.get("date", ""))
    normalized["date"] = norm_date
    if not norm_date:
        anomalies.append({
            "type": "invalid_date", "severity": "error",
            "description": date_warning or "Invalid date",
            "auto_resolved": False, "requires_user_action": True,
        })
    elif date_ambiguous:
        anomalies.append({
            "type": "ambiguous_date", "severity": "warning",
            "description": f"Date '{raw_row.get('date')}' is ambiguous (DD/MM vs MM/DD)",
            "auto_resolved": False, "requires_user_action": True,
        })
    elif date_warning:
        anomalies.append({
            "type": "date_normalized", "severity": "info",
            "description": date_warning,
            "auto_resolved": True, "auto_resolution": date_warning,
            "requires_user_action": False,
        })

    # Check for future date
    if norm_date:
        try:
            parsed = datetime.strptime(norm_date, "%Y-%m-%d").date()
            if parsed > date.today():
                anomalies.append({
                    "type": "future_date", "severity": "warning",
                    "description": f"Expense date {norm_date} is in the future",
                    "auto_resolved": False, "requires_user_action": True,
                })
        except ValueError:
            pass

    # Description
    normalized["description"] = raw_row.get("description", "").strip()

    # Amount
    norm_amount, amount_warning = normalize_amount(raw_row.get("amount", ""))
    normalized["amount"] = str(norm_amount) if norm_amount is not None else None
    if norm_amount is None:
        anomalies.append({
            "type": "invalid_amount", "severity": "error",
            "description": amount_warning or "Invalid amount",
            "auto_resolved": False, "requires_user_action": True,
        })
    elif norm_amount == Decimal("0"):
        anomalies.append({
            "type": "zero_amount", "severity": "warning",
            "description": f"Amount is zero for '{normalized['description']}' — likely a placeholder or error",
            "auto_resolved": False, "requires_user_action": True,
        })
    elif norm_amount < 0:
        anomalies.append({
            "type": "negative_amount", "severity": "warning",
            "description": f"Negative amount ({norm_amount}) — could be a refund or correction",
            "auto_resolved": False, "requires_user_action": True,
        })
    elif amount_warning:
        anomalies.append({
            "type": "amount_normalized", "severity": "info",
            "description": amount_warning,
            "auto_resolved": True, "auto_resolution": amount_warning,
            "requires_user_action": False,
        })

    # Paid By
    raw_payer = raw_row.get("paid_by", "").strip()
    if not raw_payer:
        normalized["paid_by"] = None
        anomalies.append({
            "type": "missing_payer", "severity": "error",
            "description": f"Missing payer for '{normalized['description']}' — cannot determine who paid",
            "auto_resolved": False, "requires_user_action": True,
        })
    else:
        payer_name, payer_warning, payer_needs_review = resolve_name(raw_payer, known_users)
        normalized["paid_by"] = payer_name
        if payer_warning:
            anomalies.append({
                "type": "unknown_user" if payer_needs_review else "name_normalized",
                "severity": "warning" if payer_needs_review else "info",
                "description": payer_warning,
                "auto_resolved": not payer_needs_review,
                "auto_resolution": payer_warning if not payer_needs_review else None,
                "requires_user_action": payer_needs_review,
            })

    # Currency
    norm_currency, curr_warning = normalize_currency(raw_row.get("currency", ""))
    normalized["currency"] = norm_currency
    if curr_warning and "defaulted" in (curr_warning or ""):
        anomalies.append({
            "type": "missing_currency", "severity": "info",
            "description": curr_warning,
            "auto_resolved": True, "auto_resolution": curr_warning,
            "requires_user_action": False,
        })
    elif curr_warning and "Unsupported" in (curr_warning or ""):
        anomalies.append({
            "type": "unsupported_currency", "severity": "error",
            "description": curr_warning,
            "auto_resolved": False, "requires_user_action": True,
        })

    # Split Type
    norm_split, split_warning = normalize_split_type(raw_row.get("split_type", ""))
    normalized["split_type"] = norm_split
    if split_warning and "empty" in (split_warning or "").lower():
        # Empty split type might indicate a settlement
        normalized["split_type"] = None
    elif split_warning:
        anomalies.append({
            "type": "unsupported_split_type", "severity": "error",
            "description": split_warning,
            "auto_resolved": False, "requires_user_action": False,
        })

    # Split With (participants)
    raw_split_with = raw_row.get("split_with", "")
    participants = []
    participant_warnings = []
    if raw_split_with:
        raw_names = [n.strip() for n in raw_split_with.split(";") if n.strip()]
        for rn in raw_names:
            resolved, pw, needs_review = resolve_name(rn, known_users)
            participants.append(resolved)
            if pw and needs_review:
                participant_warnings.append(pw)
                anomalies.append({
                    "type": "unknown_user", "severity": "warning",
                    "description": pw,
                    "auto_resolved": False, "requires_user_action": True,
                })
            elif pw:
                anomalies.append({
                    "type": "name_normalized", "severity": "info",
                    "description": pw,
                    "auto_resolved": True, "auto_resolution": pw,
                    "requires_user_action": False,
                })
    normalized["participants"] = participants

    # Split Details
    raw_details = raw_row.get("split_details", "")
    split_details, details_warning = parse_split_details(raw_details, norm_split or "")
    normalized["split_details"] = split_details
    if details_warning:
        anomalies.append({
            "type": "split_parse_error", "severity": "warning",
            "description": details_warning,
            "auto_resolved": False, "requires_user_action": True,
        })

    # Validate percentage splits sum to 100
    if norm_split == "percentage" and split_details:
        pct_sum = sum(d["value"] for d in split_details if d.get("is_percentage"))
        if abs(pct_sum - 100.0) > 0.01:
            anomalies.append({
                "type": "invalid_percentage_split", "severity": "error",
                "description": f"Percentage split totals {pct_sum}% (expected 100%)",
                "auto_resolved": False, "requires_user_action": True,
            })

    # Validate unequal split totals match amount
    if norm_split == "unequal" and split_details and norm_amount:
        detail_sum = sum(Decimal(str(d["value"])) for d in split_details if not d.get("is_percentage"))
        if abs(detail_sum - norm_amount) > Decimal("0.01"):
            anomalies.append({
                "type": "split_total_mismatch", "severity": "warning",
                "description": f"Split details sum ({detail_sum}) differs from expense amount ({norm_amount})",
                "auto_resolved": False, "requires_user_action": True,
            })

    # Check for conflicting split_type and split_details
    if norm_split == "equal" and split_details:
        # Equal split with details — check if details are redundant (all same units)
        values = [d["value"] for d in split_details]
        if len(set(values)) == 1:
            anomalies.append({
                "type": "redundant_split_details", "severity": "info",
                "description": f"Split type is 'equal' with redundant share details (all equal) — treating as equal split",
                "auto_resolved": True,
                "auto_resolution": "Ignored redundant split details for equal split",
                "requires_user_action": False,
            })
        else:
            anomalies.append({
                "type": "conflicting_split_info", "severity": "warning",
                "description": f"Split type is 'equal' but split details suggest unequal shares",
                "auto_resolved": False, "requires_user_action": True,
            })

    # Notes
    normalized["notes"] = raw_row.get("notes", "").strip()

    return normalized, anomalies
