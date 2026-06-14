from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional


class SettlementCreate(BaseModel):
    payer_id: str
    payee_id: str
    amount: float
    currency: str = "INR"
    settlement_date: date
    notes: Optional[str] = None


class SettlementOut(BaseModel):
    id: str
    group_id: str
    payer_id: str
    payer_name: str = ""
    payee_id: str
    payee_name: str = ""
    amount: float
    currency: str
    settlement_date: date
    notes: Optional[str] = None
    import_session_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
