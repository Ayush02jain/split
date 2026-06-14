from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date
from decimal import Decimal
from typing import Optional
from collections import defaultdict

from app.database import get_db
from app.models.user import User
from app.models.expense import Expense, ExpenseParticipant, ExpenseCategory
from app.models.settlement import Settlement
from app.models.group import GroupMembership
from app.utils.security import get_current_user

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/groups/{group_id}/analytics/by-category")
def analytics_by_category(
    group_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Total spending breakdown by category."""
    query = db.query(Expense).filter(
        Expense.group_id == group_id,
        Expense.is_deleted == False,
    )
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)

    expenses = query.all()

    category_totals = defaultdict(lambda: {"total": Decimal("0"), "count": 0})
    uncategorized = {"total": Decimal("0"), "count": 0}
    grand_total = Decimal("0")

    for e in expenses:
        effective = e.converted_amount if e.converted_amount else e.amount
        grand_total += effective

        if e.category_id:
            cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == e.category_id).first()
            cat_name = cat.name if cat else "Unknown"
            cat_icon = cat.icon if cat else "❓"
            key = (e.category_id, cat_name, cat_icon)
            category_totals[key]["total"] += effective
            category_totals[key]["count"] += 1
        else:
            uncategorized["total"] += effective
            uncategorized["count"] += 1

    result = []
    for (cat_id, cat_name, cat_icon), data in sorted(
        category_totals.items(), key=lambda x: x[1]["total"], reverse=True
    ):
        pct = float(data["total"] / grand_total * 100) if grand_total else 0
        result.append({
            "category_id": cat_id,
            "category_name": cat_name,
            "icon": cat_icon,
            "total": float(data["total"]),
            "count": data["count"],
            "percentage": round(pct, 1),
        })

    if uncategorized["count"] > 0:
        pct = float(uncategorized["total"] / grand_total * 100) if grand_total else 0
        result.append({
            "category_id": None,
            "category_name": "Uncategorized",
            "icon": "📦",
            "total": float(uncategorized["total"]),
            "count": uncategorized["count"],
            "percentage": round(pct, 1),
        })

    return {
        "group_id": group_id,
        "grand_total": float(grand_total),
        "categories": result,
    }


@router.get("/groups/{group_id}/analytics/trends")
def analytics_trends(
    group_id: str,
    period: str = Query(default="monthly", description="monthly or weekly"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Spending trends over time — monthly or weekly breakdowns."""
    query = db.query(Expense).filter(
        Expense.group_id == group_id,
        Expense.is_deleted == False,
    )
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)

    expenses = query.order_by(Expense.expense_date).all()

    buckets = defaultdict(lambda: {"total": Decimal("0"), "count": 0})

    for e in expenses:
        effective = e.converted_amount if e.converted_amount else e.amount
        if period == "weekly":
            # ISO week: YYYY-WNN
            iso = e.expense_date.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
        else:
            # Monthly: YYYY-MM
            key = e.expense_date.strftime("%Y-%m")

        buckets[key]["total"] += effective
        buckets[key]["count"] += 1

    result = []
    for key in sorted(buckets.keys()):
        result.append({
            "period": key,
            "total": float(buckets[key]["total"]),
            "count": buckets[key]["count"],
        })

    return {
        "group_id": group_id,
        "period_type": period,
        "trends": result,
    }


@router.get("/groups/{group_id}/analytics/member-contributions")
def analytics_member_contributions(
    group_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Member-wise contribution summary — how much each member paid and owes."""
    query = db.query(Expense).filter(
        Expense.group_id == group_id,
        Expense.is_deleted == False,
    )
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)

    expenses = query.all()

    # Track: total paid by each user, total share owed by each user
    paid_by = defaultdict(Decimal)
    share_of = defaultdict(Decimal)
    expense_count = defaultdict(int)

    for e in expenses:
        effective = e.converted_amount if e.converted_amount else e.amount
        paid_by[e.paid_by] += effective
        expense_count[e.paid_by] += 1

        for p in e.participants:
            share_of[p.user_id] += p.share_amount

    # Settlements
    settlements = db.query(Settlement).filter(Settlement.group_id == group_id).all()
    settled_paid = defaultdict(Decimal)
    settled_received = defaultdict(Decimal)
    for s in settlements:
        settled_paid[s.payer_id] += s.amount
        settled_received[s.payee_id] += s.amount

    # Build result
    all_user_ids = set(paid_by.keys()) | set(share_of.keys())
    result = []
    for uid in all_user_ids:
        user = db.query(User).filter(User.id == uid).first()
        name = user.display_name if user else "Unknown"
        total_paid = float(paid_by.get(uid, Decimal("0")))
        total_share = float(share_of.get(uid, Decimal("0")))
        result.append({
            "user_id": uid,
            "display_name": name,
            "total_paid": total_paid,
            "total_share": total_share,
            "net_contribution": round(total_paid - total_share, 2),
            "expenses_paid_count": expense_count.get(uid, 0),
            "settlements_paid": float(settled_paid.get(uid, Decimal("0"))),
            "settlements_received": float(settled_received.get(uid, Decimal("0"))),
        })

    # Sort by net contribution (biggest contributor first)
    result.sort(key=lambda x: x["net_contribution"], reverse=True)

    return {
        "group_id": group_id,
        "members": result,
    }
