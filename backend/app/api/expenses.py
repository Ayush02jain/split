from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.expense import Expense, ExpenseParticipant, ExpenseCategory
from app.models.group import GroupMembership
from app.schemas.expense import (
    ExpenseCreate, ExpenseUpdate, ExpenseOut, ParticipantOut,
    BalanceSummary, BalanceEntry, CategoryOut,
)
from app.utils.security import get_current_user
from app.services.balance import compute_group_balances, calculate_shares, round_money
from app.config import settings

router = APIRouter(prefix="/api", tags=["expenses"])


@router.post("/groups/{group_id}/expenses", response_model=ExpenseOut)
def create_expense(group_id: str, data: ExpenseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Currency conversion
    converted_amount = None
    exchange_rate = None
    amount = Decimal(str(data.amount))

    if data.currency == "USD":
        exchange_rate = Decimal(str(settings.USD_TO_INR_RATE))
        converted_amount = round_money(amount * exchange_rate)

    expense = Expense(
        group_id=group_id,
        title=data.title,
        description=data.description,
        amount=amount,
        currency=data.currency,
        converted_amount=converted_amount,
        exchange_rate=exchange_rate,
        paid_by=data.paid_by,
        split_type=data.split_type,
        expense_date=data.expense_date,
        category_id=data.category_id,
    )
    db.add(expense)
    db.flush()

    # Calculate and create participants
    effective_amount = converted_amount if converted_amount else amount

    if data.split_type == "equal":
        participants_list = [p.user_id for p in data.participants]
        shares = calculate_shares(effective_amount, "equal", participants_list)
        for p in data.participants:
            ep = ExpenseParticipant(
                expense_id=expense.id,
                user_id=p.user_id,
                share_amount=shares.get(p.user_id, Decimal("0")),
            )
            db.add(ep)
    else:
        split_details = []
        for p in data.participants:
            split_details.append({
                "user_id": p.user_id,
                "share_amount": p.share_amount or 0,
                "share_percentage": p.share_percentage or 0,
                "share_units": p.share_units or 1,
            })
        shares = calculate_shares(effective_amount, data.split_type, split_details, split_details)
        for p in data.participants:
            ep = ExpenseParticipant(
                expense_id=expense.id,
                user_id=p.user_id,
                share_amount=shares.get(p.user_id, Decimal("0")),
                share_percentage=Decimal(str(p.share_percentage)) if p.share_percentage else None,
                share_units=p.share_units,
            )
            db.add(ep)

    db.commit()
    db.refresh(expense)
    return _build_expense_out(expense, db)


@router.get("/groups/{group_id}/expenses", response_model=list[ExpenseOut])
def list_expenses(
    group_id: str,
    category_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Expense).filter(
        Expense.group_id == group_id,
        Expense.is_deleted == False,
    )
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)

    expenses = query.order_by(Expense.expense_date.desc()).all()
    return [_build_expense_out(e, db) for e in expenses]


@router.get("/expenses/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return _build_expense_out(expense, db)


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: str, data: ExpenseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if data.title is not None:
        expense.title = data.title
    if data.description is not None:
        expense.description = data.description
    if data.amount is not None:
        expense.amount = Decimal(str(data.amount))
    if data.currency is not None:
        expense.currency = data.currency
    if data.paid_by is not None:
        expense.paid_by = data.paid_by
    if data.split_type is not None:
        expense.split_type = data.split_type
    if data.expense_date is not None:
        expense.expense_date = data.expense_date
    if data.category_id is not None:
        expense.category_id = data.category_id

    # Handle currency conversion
    if expense.currency == "USD":
        expense.exchange_rate = Decimal(str(settings.USD_TO_INR_RATE))
        expense.converted_amount = round_money(expense.amount * expense.exchange_rate)
    else:
        expense.exchange_rate = None
        expense.converted_amount = None

    # Recalculate participants if provided
    if data.participants is not None:
        db.query(ExpenseParticipant).filter(ExpenseParticipant.expense_id == expense.id).delete()
        effective_amount = expense.converted_amount if expense.converted_amount else expense.amount

        if expense.split_type == "equal":
            participants_list = [p.user_id for p in data.participants]
            shares = calculate_shares(effective_amount, "equal", participants_list)
            for p in data.participants:
                ep = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=p.user_id,
                    share_amount=shares.get(p.user_id, Decimal("0")),
                )
                db.add(ep)
        else:
            split_details = [{"user_id": p.user_id, "share_amount": p.share_amount or 0,
                              "share_percentage": p.share_percentage or 0, "share_units": p.share_units or 1}
                             for p in data.participants]
            shares = calculate_shares(effective_amount, expense.split_type, split_details, split_details)
            for p in data.participants:
                ep = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=p.user_id,
                    share_amount=shares.get(p.user_id, Decimal("0")),
                    share_percentage=Decimal(str(p.share_percentage)) if p.share_percentage else None,
                    share_units=p.share_units,
                )
                db.add(ep)

    db.commit()
    db.refresh(expense)
    return _build_expense_out(expense, db)


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    expense.is_deleted = True
    db.commit()
    return {"detail": "Expense deleted"}


# --- Balances ---

@router.get("/groups/{group_id}/balances", response_model=BalanceSummary)
def get_group_balances(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = compute_group_balances(db, group_id)

    balances = []
    for uid, bal in result["balances"].items():
        user = db.query(User).filter(User.id == uid).first()
        name = user.display_name if user else "Unknown"
        balances.append(BalanceEntry(user_id=uid, display_name=name, net_balance=bal))

    debts = []
    for d in result["debts"]:
        from_user = db.query(User).filter(User.id == d["from_user"]).first()
        to_user = db.query(User).filter(User.id == d["to_user"]).first()
        debts.append({
            "from_user": d["from_user"],
            "from_name": from_user.display_name if from_user else "Unknown",
            "to_user": d["to_user"],
            "to_name": to_user.display_name if to_user else "Unknown",
            "amount": d["amount"],
        })

    return BalanceSummary(group_id=group_id, balances=balances, debts=debts)


@router.get("/groups/{group_id}/balances/traces")
def get_balance_traces(group_id: str, user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get expense trace for a specific user's balance - which expenses contributed."""
    result = compute_group_balances(db, group_id)
    traces = result["expense_traces"].get(user_id, [])

    # Enrich with payer names
    for t in traces:
        payer = db.query(User).filter(User.id == t["paid_by"]).first()
        t["payer_name"] = payer.display_name if payer else "Unknown"

    return {"user_id": user_id, "traces": traces}


# --- Categories ---

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cats = db.query(ExpenseCategory).order_by(ExpenseCategory.name).all()
    return [CategoryOut.model_validate(c) for c in cats]


def _build_expense_out(expense: Expense, db: Session) -> ExpenseOut:
    payer = db.query(User).filter(User.id == expense.paid_by).first()
    category = db.query(ExpenseCategory).filter(ExpenseCategory.id == expense.category_id).first() if expense.category_id else None

    participants = []
    for p in expense.participants:
        user = db.query(User).filter(User.id == p.user_id).first()
        participants.append(ParticipantOut(
            user_id=p.user_id,
            display_name=user.display_name if user else "Unknown",
            share_amount=float(p.share_amount),
            share_percentage=float(p.share_percentage) if p.share_percentage else None,
            share_units=p.share_units,
        ))

    return ExpenseOut(
        id=expense.id,
        group_id=expense.group_id,
        title=expense.title,
        description=expense.description,
        amount=float(expense.amount),
        currency=expense.currency,
        converted_amount=float(expense.converted_amount) if expense.converted_amount else None,
        exchange_rate=float(expense.exchange_rate) if expense.exchange_rate else None,
        paid_by=expense.paid_by,
        payer_name=payer.display_name if payer else "Unknown",
        split_type=expense.split_type,
        expense_date=expense.expense_date,
        category_id=expense.category_id,
        category_name=category.name if category else None,
        import_session_id=expense.import_session_id,
        source_row_number=expense.source_row_number,
        participants=participants,
        created_at=expense.created_at,
    )
