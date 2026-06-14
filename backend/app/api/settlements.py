from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from app.database import get_db
from app.models.user import User
from app.models.settlement import Settlement
from app.schemas.settlement import SettlementCreate, SettlementOut
from app.utils.security import get_current_user

router = APIRouter(prefix="/api", tags=["settlements"])


@router.post("/groups/{group_id}/settlements", response_model=SettlementOut)
def create_settlement(group_id: str, data: SettlementCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settlement = Settlement(
        group_id=group_id,
        payer_id=data.payer_id,
        payee_id=data.payee_id,
        amount=Decimal(str(data.amount)),
        currency=data.currency,
        settlement_date=data.settlement_date,
        notes=data.notes,
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return _build_settlement_out(settlement, db)


@router.get("/groups/{group_id}/settlements", response_model=list[SettlementOut])
def list_settlements(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settlements = db.query(Settlement).filter(
        Settlement.group_id == group_id
    ).order_by(Settlement.settlement_date.desc()).all()
    return [_build_settlement_out(s, db) for s in settlements]


@router.delete("/settlements/{settlement_id}")
def delete_settlement(settlement_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    settlement = db.query(Settlement).filter(Settlement.id == settlement_id).first()
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")
    db.delete(settlement)
    db.commit()
    return {"detail": "Settlement deleted"}


def _build_settlement_out(settlement: Settlement, db: Session) -> SettlementOut:
    payer = db.query(User).filter(User.id == settlement.payer_id).first()
    payee = db.query(User).filter(User.id == settlement.payee_id).first()
    return SettlementOut(
        id=settlement.id,
        group_id=settlement.group_id,
        payer_id=settlement.payer_id,
        payer_name=payer.display_name if payer else "Unknown",
        payee_id=settlement.payee_id,
        payee_name=payee.display_name if payee else "Unknown",
        amount=float(settlement.amount),
        currency=settlement.currency,
        settlement_date=settlement.settlement_date,
        notes=settlement.notes,
        import_session_id=settlement.import_session_id,
        created_at=settlement.created_at,
    )
