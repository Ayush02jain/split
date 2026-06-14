from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class ImportSessionOut(BaseModel):
    id: str
    group_id: str
    file_name: str
    status: str
    total_rows: int
    imported_expenses: int
    imported_settlements: int
    detected_anomalies: int
    pending_reviews: int
    skipped_rows: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ImportedRecordOut(BaseModel):
    id: str
    row_number: int
    raw_data: Optional[Dict[str, Any]] = None
    normalized_data: Optional[Dict[str, Any]] = None
    status: str
    result_type: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ImportAnomalyOut(BaseModel):
    id: str
    imported_record_id: Optional[str] = None
    anomaly_type: str
    severity: str
    description: str
    auto_resolved: bool
    auto_resolution: Optional[str] = None
    requires_user_action: bool
    related_record_ids: Optional[Dict] = None
    resolution: Optional[Dict] = None
    row_number: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ConflictResolutionIn(BaseModel):
    action: str  # keep, skip, merge, edit, convert_to_settlement, assign_payer, select_mapping, confirm
    details: Optional[Dict[str, Any]] = None


class ImportPreviewOut(BaseModel):
    session_id: str
    file_name: str
    total_rows: int
    valid_expenses: int
    valid_settlements: int
    auto_resolved: int
    needs_review: int
    skipped: int
    records: List[ImportedRecordOut] = []
    anomalies: List[ImportAnomalyOut] = []


class ImportReportOut(BaseModel):
    session_id: str
    file_name: str
    status: str
    total_rows: int
    expenses_imported: int
    settlements_imported: int
    duplicates_detected: int
    currency_conversions: int
    negative_amounts: int
    invalid_rows_skipped: int
    unknown_members: int
    manual_reviews: int
    anomaly_details: List[ImportAnomalyOut] = []
