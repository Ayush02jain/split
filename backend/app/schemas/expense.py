from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict


class ParticipantIn(BaseModel):
    user_id: str
    share_amount: Optional[float] = None
    share_percentage: Optional[float] = None
    share_units: Optional[int] = None


class ExpenseCreate(BaseModel):
    title: str
    amount: float
    currency: str = "INR"
    paid_by: str
    split_type: str
    expense_date: date
    participants: List[ParticipantIn]
    description: Optional[str] = None
    category_id: Optional[str] = None


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    paid_by: Optional[str] = None
    split_type: Optional[str] = None
    expense_date: Optional[date] = None
    participants: Optional[List[ParticipantIn]] = None
    description: Optional[str] = None
    category_id: Optional[str] = None


class ParticipantOut(BaseModel):
    user_id: str
    display_name: str
    share_amount: float
    share_percentage: Optional[float] = None
    share_units: Optional[int] = None

    class Config:
        from_attributes = True


class ExpenseOut(BaseModel):
    id: str
    group_id: str
    title: str
    description: Optional[str] = None
    amount: float
    currency: str
    converted_amount: Optional[float] = None
    exchange_rate: Optional[float] = None
    paid_by: str
    payer_name: str = ""
    split_type: str
    expense_date: date
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    import_session_id: Optional[str] = None
    source_row_number: Optional[int] = None
    participants: List[ParticipantOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class BalanceEntry(BaseModel):
    user_id: str
    display_name: str
    net_balance: float  # positive = owed money, negative = owes money


class BalanceSummary(BaseModel):
    group_id: str
    balances: List[BalanceEntry]
    debts: List[Dict]  # [{from_user, from_name, to_user, to_name, amount}]


class CategoryOut(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None

    class Config:
        from_attributes = True
