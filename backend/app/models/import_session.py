import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Text, Numeric, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class ImportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecordStatus(str, enum.Enum):
    VALID = "valid"
    IMPORTED = "imported"
    SKIPPED = "skipped"
    ERROR = "error"
    PENDING_REVIEW = "pending_review"
    DUPLICATE = "duplicate"


class ResultType(str, enum.Enum):
    EXPENSE = "expense"
    SETTLEMENT = "settlement"
    SKIPPED = "skipped"


class AnomalySeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ImportSession(Base):
    __tablename__ = "import_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id"), nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=ImportStatus.PENDING.value)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_expenses: Mapped[int] = mapped_column(Integer, default=0)
    imported_settlements: Mapped[int] = mapped_column(Integer, default=0)
    detected_anomalies: Mapped[int] = mapped_column(Integer, default=0)
    pending_reviews: Mapped[int] = mapped_column(Integer, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    records = relationship("ImportedRecord", back_populates="import_session", cascade="all, delete-orphan")
    anomalies = relationship("ImportAnomaly", back_populates="import_session", cascade="all, delete-orphan")
    initiator = relationship("User", foreign_keys=[initiated_by])


class ImportedRecord(Base):
    __tablename__ = "imported_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    import_session_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_sessions.id"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    normalized_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=RecordStatus.VALID.value)
    result_type: Mapped[str] = mapped_column(String(20), nullable=True)
    result_id: Mapped[str] = mapped_column(String(36), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    import_session = relationship("ImportSession", back_populates="records")
    anomalies = relationship("ImportAnomaly", back_populates="imported_record")


class ImportAnomaly(Base):
    __tablename__ = "import_anomalies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    import_session_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_sessions.id"), nullable=False)
    imported_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("imported_records.id"), nullable=True)
    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default=AnomalySeverity.WARNING.value)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    auto_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_resolution: Mapped[str] = mapped_column(Text, nullable=True)
    requires_user_action: Mapped[bool] = mapped_column(Boolean, default=False)
    related_record_ids: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    import_session = relationship("ImportSession", back_populates="anomalies")
    imported_record = relationship("ImportedRecord", back_populates="anomalies")
    resolution = relationship("ImportConflictResolution", back_populates="anomaly", uselist=False)


class ImportConflictResolution(Base):
    __tablename__ = "import_conflict_resolutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    anomaly_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_anomalies.id"), nullable=False)
    resolved_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    anomaly = relationship("ImportAnomaly", back_populates="resolution")
    resolver = relationship("User")
