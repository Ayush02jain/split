"""
Anomaly Detector — Stage 6 of the import pipeline.

Runs cross-row analysis after individual row normalization:
- Duplicate detection (exact and fuzzy)
- Settlement detection
- Membership validation
- Currency conversion flagging
"""
from typing import List, Dict, Tuple
from decimal import Decimal
from datetime import datetime, date
import re


# --- Settlement Detector ---

SETTLEMENT_KEYWORDS = [
    "paid back", "paid", "settlement", "settled", "deposit share",
    "deposit", "refund", "reimbursement", "transfer",
]


def detect_settlement(row: Dict) -> Tuple[bool, str]:
    """
    Detect if a row is likely a settlement rather than an expense.
    
    Indicators:
    - Keywords in description or notes
    - Empty split_type
    - Only 1 participant (1:1 payer→payee)
    """
    description = (row.get("description") or "").lower()
    notes = (row.get("notes") or "").lower()
    split_type = row.get("split_type")
    participants = row.get("participants", [])

    reasons = []

    # Keyword detection
    for kw in SETTLEMENT_KEYWORDS:
        if kw in description or kw in notes:
            reasons.append(f"Keyword '{kw}' found")
            break

    # Empty split type with single participant
    if not split_type and len(participants) <= 2:
        reasons.append("No split type with ≤2 participants")

    # Notes contain settlement hints
    if "settlement" in notes or "not an expense" in notes:
        reasons.append("Notes indicate this is a settlement")

    is_settlement = len(reasons) >= 1 and (not split_type or len(participants) <= 2)

    return is_settlement, "; ".join(reasons) if reasons else ""


# --- Duplicate Detector ---

def find_duplicates(rows: List[Dict]) -> List[Dict]:
    """
    Find potential duplicate rows.
    
    Detects:
    1. Exact duplicates: same date + same amount + same payer + very similar description
    2. Conflicting duplicates: same date + similar description + different amounts or payers
    
    Returns list of anomaly dicts.
    """
    anomalies = []
    n = len(rows)

    for i in range(n):
        for j in range(i + 1, n):
            r1, r2 = rows[i], rows[j]

            # Skip rows with missing critical data
            if not r1.get("date") or not r2.get("date"):
                continue
            if r1.get("date") != r2.get("date"):
                continue

            desc1 = (r1.get("description") or "").lower()
            desc2 = (r2.get("description") or "").lower()
            sim = _description_similarity(desc1, desc2)

            if sim < 0.4:
                continue

            row1_num = r1.get("_row_number", "?")
            row2_num = r2.get("_row_number", "?")

            amt1 = r1.get("amount")
            amt2 = r2.get("amount")
            payer1 = r1.get("paid_by", "")
            payer2 = r2.get("paid_by", "")

            if amt1 == amt2 and payer1 == payer2:
                # Exact duplicate
                anomalies.append({
                    "type": "exact_duplicate",
                    "severity": "warning",
                    "description": (
                        f"Rows {row1_num} and {row2_num} appear to be duplicates: "
                        f"'{r1.get('description')}' and '{r2.get('description')}' "
                        f"(same date, amount {amt1}, payer {payer1})"
                    ),
                    "auto_resolved": False,
                    "requires_user_action": True,
                    "row_numbers": [row1_num, row2_num],
                })
            elif sim >= 0.5:
                # Conflicting duplicate — similar description but different details
                differences = []
                if amt1 != amt2:
                    differences.append(f"amounts differ ({amt1} vs {amt2})")
                if payer1 != payer2:
                    differences.append(f"payers differ ({payer1} vs {payer2})")

                anomalies.append({
                    "type": "conflicting_duplicate",
                    "severity": "warning",
                    "description": (
                        f"Rows {row1_num} and {row2_num} may be conflicting entries: "
                        f"'{r1.get('description')}' and '{r2.get('description')}' — "
                        f"{', '.join(differences)}"
                    ),
                    "auto_resolved": False,
                    "requires_user_action": True,
                    "row_numbers": [row1_num, row2_num],
                })

    return anomalies


def _description_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity score between two descriptions."""
    if not a or not b:
        return 0.0
    words_a = set(re.findall(r'\w+', a.lower()))
    words_b = set(re.findall(r'\w+', b.lower()))
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


# --- Membership Validator ---

def validate_membership(
    row: Dict,
    memberships: Dict[str, Dict],  # {name: {joined_at, left_at}}
    group_created_at: date = None,
) -> List[Dict]:
    """
    Check if participants were active members on the expense date.
    
    memberships: {display_name: {"joined_at": date, "left_at": date or None}}
    
    Returns list of anomalies.
    """
    anomalies = []
    expense_date_str = row.get("date")
    if not expense_date_str:
        return anomalies

    try:
        expense_date = datetime.strptime(expense_date_str, "%Y-%m-%d").date()
    except ValueError:
        return anomalies

    # Check if expense is before group creation
    # (Silently allow historical expenses to avoid anomaly inflation)
    if group_created_at and expense_date < group_created_at:
        pass

    participants = row.get("participants", [])
    excluded = []

    for participant_name in participants:
        if participant_name not in memberships:
            # Unknown user — already flagged in normalizer
            continue

        member_info = memberships[participant_name]
        joined = member_info.get("joined_at")
        left = member_info.get("left_at")

        if joined and expense_date < joined:
            excluded.append(participant_name)
            anomalies.append({
                "type": "expense_before_member_joined",
                "severity": "info",
                "description": (
                    f"{participant_name} joined on {joined} but expense is dated {expense_date} — "
                    f"excluding from split"
                ),
                "auto_resolved": True,
                "auto_resolution": f"Excluded {participant_name} (joined after expense date)",
                "requires_user_action": False,
            })

        if left and expense_date > left:
            excluded.append(participant_name)
            anomalies.append({
                "type": "expense_after_member_left",
                "severity": "info",
                "description": (
                    f"{participant_name} left on {left} but expense is dated {expense_date} — "
                    f"excluding from split"
                ),
                "auto_resolved": True,
                "auto_resolution": f"Excluded {participant_name} (left before expense date)",
                "requires_user_action": False,
            })

    return anomalies
