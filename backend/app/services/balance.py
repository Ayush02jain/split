"""
Balance calculation engine.

Computes net balances for each member in a group by iterating over all
expenses and settlements. The result is a set of "who owes whom how much"
debts, fully traceable to underlying expenses.
"""
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.expense import Expense, ExpenseParticipant
from app.models.settlement import Settlement
from app.models.user import User
from app.models.group import GroupMembership


TWO_PLACES = Decimal("0.01")


def round_money(amount: Decimal) -> Decimal:
    """Round to 2 decimal places using half-up (standard financial rounding)."""
    return Decimal(str(amount)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_shares(amount: Decimal, split_type: str, participants: list, split_details: dict = None) -> dict:
    """
    Calculate each participant's share of an expense.
    Returns dict of {user_id: share_amount}.
    
    Split types:
    - equal: divide equally, remainder goes to first participant
    - unequal: exact amounts specified per participant
    - percentage: percentage of total per participant (must sum to 100)
    - share: proportional based on unit counts
    """
    amount = Decimal(str(amount))
    shares = {}

    if split_type == "equal":
        n = len(participants)
        if n == 0:
            return shares
        per_person = round_money(amount / n)
        total_distributed = per_person * n
        remainder = round_money(amount - total_distributed)

        for i, p in enumerate(participants):
            uid = p if isinstance(p, str) else p.get("user_id", p)
            shares[uid] = per_person
        # Assign remainder to first participant (the payer typically)
        if remainder != 0 and participants:
            first_uid = participants[0] if isinstance(participants[0], str) else participants[0].get("user_id")
            shares[first_uid] = round_money(shares[first_uid] + remainder)

    elif split_type == "unequal":
        if split_details:
            for p in split_details:
                uid = p.get("user_id")
                shares[uid] = round_money(Decimal(str(p.get("share_amount", 0))))

    elif split_type == "percentage":
        if split_details:
            for p in split_details:
                uid = p.get("user_id")
                pct = Decimal(str(p.get("share_percentage", 0)))
                shares[uid] = round_money(amount * pct / Decimal("100"))

    elif split_type == "share":
        if split_details:
            total_units = sum(p.get("share_units", 1) for p in split_details)
            if total_units > 0:
                for p in split_details:
                    uid = p.get("user_id")
                    units = p.get("share_units", 1)
                    shares[uid] = round_money(amount * Decimal(str(units)) / Decimal(str(total_units)))

    return shares


def compute_group_balances(db: Session, group_id: str) -> dict:
    """
    Compute net balances for a group.
    
    For each expense:
    - The payer is OWED money by each participant (except themselves)
    - Each participant OWES their share to the payer
    
    For each settlement:
    - The payer reduces the amount they owe to the payee
    
    Returns:
    {
        "balances": {user_id: net_balance},  # positive = owed money (others owe you)
        "debts": [{from_user, to_user, amount}],
        "expense_traces": {user_id: [{expense_id, title, amount, your_share, paid_by}]}
    }
    """
    # Net balance tracker: positive = others owe you, negative = you owe others
    # Track pairwise: ledger[A][B] = amount A owes B
    ledger = defaultdict(lambda: defaultdict(Decimal))
    expense_traces = defaultdict(list)

    # Process all non-deleted expenses
    expenses = db.query(Expense).filter(
        Expense.group_id == group_id,
        Expense.is_deleted == False,
    ).all()

    for expense in expenses:
        payer_id = expense.paid_by
        # Use converted_amount if available (for foreign currency), else original amount
        effective_amount = expense.converted_amount if expense.converted_amount else expense.amount

        for participant in expense.participants:
            if participant.user_id != payer_id:
                # This participant owes the payer their share
                share = participant.share_amount
                ledger[participant.user_id][payer_id] += share

            # Record trace for every participant
            expense_traces[participant.user_id].append({
                "expense_id": expense.id,
                "title": expense.title,
                "total_amount": float(effective_amount),
                "your_share": float(participant.share_amount),
                "paid_by": payer_id,
                "date": str(expense.expense_date),
                "currency": expense.currency,
            })

    # Process settlements
    settlements = db.query(Settlement).filter(Settlement.group_id == group_id).all()
    for s in settlements:
        # Payer paid payee, so reduce payer's debt to payee
        ledger[s.payer_id][s.payee_id] -= s.amount

    # Simplify pairwise debts (net out A→B and B→A)
    debts = []
    processed = set()
    all_users = set()
    for a in ledger:
        all_users.add(a)
        for b in ledger[a]:
            all_users.add(b)

    for a in all_users:
        for b in all_users:
            if a >= b:
                continue
            pair = (a, b)
            if pair in processed:
                continue
            processed.add(pair)

            a_owes_b = ledger[a][b]
            b_owes_a = ledger[b][a]
            net = a_owes_b - b_owes_a

            if net > Decimal("0.01"):
                debts.append({"from_user": a, "to_user": b, "amount": float(round_money(net))})
            elif net < Decimal("-0.01"):
                debts.append({"from_user": b, "to_user": a, "amount": float(round_money(abs(net)))})

    # Compute net balance per user
    net_balances = defaultdict(Decimal)
    for debt in debts:
        net_balances[debt["from_user"]] -= Decimal(str(debt["amount"]))
        net_balances[debt["to_user"]] += Decimal(str(debt["amount"]))

    return {
        "balances": {uid: float(round_money(bal)) for uid, bal in net_balances.items()},
        "debts": debts,
        "expense_traces": dict(expense_traces),
    }
