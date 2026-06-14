import os
import hashlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.import_session import (
    ImportSession, ImportedRecord, ImportAnomaly, ImportConflictResolution,
    ImportStatus,
)
from app.schemas.import_session import (
    ImportSessionOut, ImportedRecordOut, ImportAnomalyOut,
    ConflictResolutionIn, ImportPreviewOut, ImportReportOut,
)
from app.utils.security import get_current_user, require_group_admin
from app.services.import_engine.pipeline import ImportPipeline
from app.config import settings

router = APIRouter(prefix="/api", tags=["csv_import"])


@router.post("/groups/{group_id}/import/upload", response_model=ImportSessionOut)
async def upload_csv(
    group_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _admin=Depends(require_group_admin),
):
    """Upload a CSV file and process it through the import pipeline."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    file_content = content.decode("utf-8-sig")  # Handle BOM

    # Save file for audit
    file_hash = hashlib.sha256(content).hexdigest()
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_hash}_{file.filename}")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    # Run import pipeline
    pipeline = ImportPipeline(db, group_id, current_user.id)
    session = pipeline.process_file(file_content, file.filename)

    # Update file path
    session.file_path = file_path
    db.commit()

    return ImportSessionOut.model_validate(session)


@router.get("/import/{session_id}/preview", response_model=ImportPreviewOut)
def get_import_preview(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the import preview — summary of what will be imported."""
    session = db.query(ImportSession).filter(ImportSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")

    records = db.query(ImportedRecord).filter(
        ImportedRecord.import_session_id == session_id
    ).order_by(ImportedRecord.row_number).all()

    anomalies = db.query(ImportAnomaly).filter(
        ImportAnomaly.import_session_id == session_id
    ).all()

    record_outs = [ImportedRecordOut.model_validate(r) for r in records]

    anomaly_outs = []
    for a in anomalies:
        rec = db.query(ImportedRecord).filter(ImportedRecord.id == a.imported_record_id).first() if a.imported_record_id else None
        resolution = None
        if a.resolution:
            resolution = {
                "action": a.resolution.action,
                "details": a.resolution.details,
                "resolved_at": str(a.resolution.resolved_at),
            }
        anomaly_outs.append(ImportAnomalyOut(
            id=a.id,
            imported_record_id=a.imported_record_id,
            anomaly_type=a.anomaly_type,
            severity=a.severity,
            description=a.description,
            auto_resolved=a.auto_resolved,
            auto_resolution=a.auto_resolution,
            requires_user_action=a.requires_user_action,
            related_record_ids=a.related_record_ids,
            resolution=resolution,
            row_number=rec.row_number if rec else None,
            raw_data=rec.raw_data if rec else None,
        ))

    valid_expenses = len([r for r in records if r.status == "valid"])
    valid_settlements = 0  # Will be determined during commit
    auto_resolved = len([a for a in anomalies if a.auto_resolved])
    needs_review = len([a for a in anomalies if a.requires_user_action and not a.auto_resolved])
    skipped = len([r for r in records if r.status in ("error", "skipped")])

    return ImportPreviewOut(
        session_id=session.id,
        file_name=session.file_name,
        total_rows=session.total_rows,
        valid_expenses=valid_expenses,
        valid_settlements=valid_settlements,
        auto_resolved=auto_resolved,
        needs_review=needs_review,
        skipped=skipped,
        records=record_outs,
        anomalies=anomaly_outs,
    )


@router.get("/import/{session_id}/anomalies", response_model=list[ImportAnomalyOut])
def get_anomalies(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all anomalies for an import session."""
    anomalies = db.query(ImportAnomaly).filter(
        ImportAnomaly.import_session_id == session_id
    ).all()

    result = []
    for a in anomalies:
        rec = db.query(ImportedRecord).filter(ImportedRecord.id == a.imported_record_id).first() if a.imported_record_id else None
        resolution = None
        if a.resolution:
            resolution = {
                "action": a.resolution.action,
                "details": a.resolution.details,
            }
        result.append(ImportAnomalyOut(
            id=a.id,
            imported_record_id=a.imported_record_id,
            anomaly_type=a.anomaly_type,
            severity=a.severity,
            description=a.description,
            auto_resolved=a.auto_resolved,
            auto_resolution=a.auto_resolution,
            requires_user_action=a.requires_user_action,
            related_record_ids=a.related_record_ids,
            resolution=resolution,
            row_number=rec.row_number if rec else None,
            raw_data=rec.raw_data if rec else None,
        ))
    return result


@router.post("/import/conflicts/{anomaly_id}/resolve")
def resolve_conflict(
    anomaly_id: str,
    data: ConflictResolutionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve a single import conflict/anomaly."""
    anomaly = db.query(ImportAnomaly).filter(ImportAnomaly.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    # Check if already resolved
    existing = db.query(ImportConflictResolution).filter(
        ImportConflictResolution.anomaly_id == anomaly_id
    ).first()
    if existing:
        existing.action = data.action
        existing.details = data.details
    else:
        resolution = ImportConflictResolution(
            anomaly_id=anomaly_id,
            resolved_by=current_user.id,
            action=data.action,
            details=data.details,
        )
        db.add(resolution)

    # If action is skip, mark the record as skipped
    if data.action == "skip" and anomaly.imported_record_id:
        record = db.query(ImportedRecord).filter(ImportedRecord.id == anomaly.imported_record_id).first()
        if record:
            record.status = "skipped"

    # Update session pending count
    session = db.query(ImportSession).filter(ImportSession.id == anomaly.import_session_id).first()
    if session:
        unresolved = db.query(ImportAnomaly).filter(
            ImportAnomaly.import_session_id == session.id,
            ImportAnomaly.requires_user_action == True,
            ImportAnomaly.auto_resolved == False,
        ).all()
        resolved_count = 0
        for ua in unresolved:
            res = db.query(ImportConflictResolution).filter(
                ImportConflictResolution.anomaly_id == ua.id
            ).first()
            if res:
                resolved_count += 1
        session.pending_reviews = len(unresolved) - resolved_count

    db.commit()
    return {"detail": "Conflict resolved", "action": data.action}


@router.post("/import/{session_id}/confirm", response_model=ImportSessionOut)
def confirm_import(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Confirm and commit the import to the database."""
    session = db.query(ImportSession).filter(ImportSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")

    if session.status not in (ImportStatus.AWAITING_REVIEW.value, ImportStatus.PROCESSING.value):
        raise HTTPException(status_code=400, detail=f"Cannot confirm import in status: {session.status}")

    pipeline = ImportPipeline(db, session.group_id, current_user.id)
    session = pipeline.commit_import(session_id)

    return ImportSessionOut.model_validate(session)


@router.post("/import/{session_id}/cancel")
def cancel_import(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Cancel an import session."""
    session = db.query(ImportSession).filter(ImportSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")

    session.status = ImportStatus.CANCELLED.value
    db.commit()
    return {"detail": "Import cancelled"}


@router.get("/groups/{group_id}/import/history", response_model=list[ImportSessionOut])
def import_history(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get import history for a group."""
    sessions = db.query(ImportSession).filter(
        ImportSession.group_id == group_id
    ).order_by(ImportSession.created_at.desc()).all()
    return [ImportSessionOut.model_validate(s) for s in sessions]


@router.get("/import/{session_id}/report", response_model=ImportReportOut)
def get_import_report(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the final import report."""
    session = db.query(ImportSession).filter(ImportSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Import session not found")

    anomalies = db.query(ImportAnomaly).filter(
        ImportAnomaly.import_session_id == session_id
    ).all()

    anomaly_outs = []
    for a in anomalies:
        rec = db.query(ImportedRecord).filter(ImportedRecord.id == a.imported_record_id).first() if a.imported_record_id else None
        anomaly_outs.append(ImportAnomalyOut(
            id=a.id,
            imported_record_id=a.imported_record_id,
            anomaly_type=a.anomaly_type,
            severity=a.severity,
            description=a.description,
            auto_resolved=a.auto_resolved,
            auto_resolution=a.auto_resolution,
            requires_user_action=a.requires_user_action,
            related_record_ids=a.related_record_ids,
            row_number=rec.row_number if rec else None,
            raw_data=rec.raw_data if rec else None,
        ))

    # Count specific anomaly types
    dup_count = len([a for a in anomalies if "duplicate" in a.anomaly_type])
    currency_count = len([a for a in anomalies if a.anomaly_type in ("missing_currency", "currency_conversion")])
    negative_count = len([a for a in anomalies if a.anomaly_type == "negative_amount"])
    unknown_count = len([a for a in anomalies if a.anomaly_type == "unknown_user"])
    review_count = len([a for a in anomalies if a.requires_user_action])

    return ImportReportOut(
        session_id=session.id,
        file_name=session.file_name,
        status=session.status,
        total_rows=session.total_rows,
        expenses_imported=session.imported_expenses,
        settlements_imported=session.imported_settlements,
        duplicates_detected=dup_count,
        currency_conversions=currency_count,
        negative_amounts=negative_count,
        invalid_rows_skipped=session.skipped_rows,
        unknown_members=unknown_count,
        manual_reviews=review_count,
        anomaly_details=anomaly_outs,
    )
