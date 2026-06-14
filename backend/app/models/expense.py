import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Numeric, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class SplitType(str, enum.Enum):
    EQUAL = "equal"
    UNEQUAL = "unequal"
    PERCENTAGE = "percentage"
    SHARE = "share"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    converted_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)
    paid_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    split_type: Mapped[str] = mapped_column(String(20), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("expense_categories.id"), nullable=True)
    import_session_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_sessions.id"), nullable=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    group = relationship("Group", back_populates="expenses")
    payer = relationship("User", back_populates="expenses_paid")
    participants = relationship("ExpenseParticipant", back_populates="expense", cascade="all, delete-orphan")
    category = relationship("ExpenseCategory")
    import_session = relationship("ImportSession")


class ExpenseParticipant(Base):
    __tablename__ = "expense_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    expense_id: Mapped[str] = mapped_column(String(36), ForeignKey("expenses.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    share_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    share_units: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    expense = relationship("Expense", back_populates="participants")
    user = relationship("User", back_populates="participations")


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
