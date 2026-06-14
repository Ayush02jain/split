import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.expense import Expense, ExpenseParticipant, ExpenseCategory
from app.models.settlement import Settlement
from app.models.import_session import ImportSession, ImportAnomaly
from app.utils.security import get_current_user
from app.services.balance import compute_group_balances

router = APIRouter(prefix="/api", tags=["export"])


# ─── CSV Export helpers ───


def _make_csv_response(rows: list[dict], filename: str) -> StreamingResponse:
    """Build a streaming CSV response from a list of dicts."""
    if not rows:
        output = io.StringIO("No data\n")
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _make_pdf_response(title: str, headers: list[str], rows: list[list], filename: str) -> StreamingResponse:
    """Build a streaming PDF response using reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # Table
    table_data = [headers] + rows
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Expense Export ───


@router.get("/groups/{group_id}/export/expenses")
def export_expenses(
    group_id: str,
    format: str = Query(default="csv", description="csv or pdf"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export group expense history as CSV or PDF."""
    query = db.query(Expense).filter(
        Expense.group_id == group_id,
        Expense.is_deleted == False,
    )
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)

    expenses = query.order_by(Expense.expense_date).all()

    rows = []
    for e in expenses:
        payer = db.query(User).filter(User.id == e.paid_by).first()
        cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == e.category_id).first() if e.category_id else None
        participants = []
        for p in e.participants:
            u = db.query(User).filter(User.id == p.user_id).first()
            participants.append(f"{u.display_name if u else '?'} (₹{p.share_amount})")

        rows.append({
            "Date": str(e.expense_date),
            "Title": e.title,
            "Amount": float(e.amount),
            "Currency": e.currency,
            "Converted (INR)": float(e.converted_amount) if e.converted_amount else "",
            "Paid By": payer.display_name if payer else "Unknown",
            "Split Type": e.split_type,
            "Category": cat.name if cat else "",
            "Participants": "; ".join(participants),
            "Notes": e.description or "",
            "Source": f"Import Row {e.source_row_number}" if e.source_row_number else "Manual",
        })

    filename = f"expenses_{group_id[:8]}_{date.today()}"

    if format == "pdf":
        headers = list(rows[0].keys()) if rows else []
        pdf_rows = [[str(r.get(h, "")) for h in headers] for r in rows]
        return _make_pdf_response("Expense History", headers, pdf_rows, f"{filename}.pdf")

    return _make_csv_response(rows, f"{filename}.csv")


# ─── Balance Export ───


@router.get("/groups/{group_id}/export/balances")
def export_balances(
    group_id: str,
    format: str = Query(default="csv", description="csv or pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export group balance summary as CSV or PDF."""
    result = compute_group_balances(db, group_id)

    # Balance rows
    balance_rows = []
    for uid, bal in result["balances"].items():
        user = db.query(User).filter(User.id == uid).first()
        name = user.display_name if user else "Unknown"
        status = "Receives" if bal > 0 else "Owes" if bal < 0 else "Settled"
        balance_rows.append({
            "Member": name,
            "Net Balance (₹)": bal,
            "Status": status,
        })

    # Debt rows
    debt_rows = []
    for d in result["debts"]:
        from_user = db.query(User).filter(User.id == d["from_user"]).first()
        to_user = db.query(User).filter(User.id == d["to_user"]).first()
        debt_rows.append({
            "From": from_user.display_name if from_user else "Unknown",
            "To": to_user.display_name if to_user else "Unknown",
            "Amount (₹)": d["amount"],
        })

    filename = f"balances_{group_id[:8]}_{date.today()}"

    if format == "pdf":
        # Combine into one PDF
        headers = ["Member", "Net Balance (₹)", "Status"]
        pdf_rows = [[str(r.get(h, "")) for h in headers] for r in balance_rows]
        return _make_pdf_response("Balance Summary", headers, pdf_rows, f"{filename}.pdf")

    # CSV: combine balance and debt info
    combined = []
    for b in balance_rows:
        combined.append({"Type": "Balance", **b, "From": "", "To": ""})
    for d in debt_rows:
        combined.append({"Type": "Debt", "Member": "", "Net Balance (₹)": d["Amount (₹)"],
                         "Status": "", "From": d["From"], "To": d["To"]})

    return _make_csv_response(combined if combined else [{"Message": "No balances"}], f"{filename}.csv")


# ─── Settlement Export ───


@router.get("/groups/{group_id}/export/settlements")
def export_settlements(
    group_id: str,
    format: str = Query(default="csv", description="csv or pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export settlement history as CSV or PDF."""
    settlements = db.query(Settlement).filter(
        Settlement.group_id == group_id,
    ).order_by(Settlement.settlement_date).all()

    rows = []
    for s in settlements:
        payer = db.query(User).filter(User.id == s.payer_id).first()
        payee = db.query(User).filter(User.id == s.payee_id).first()
        rows.append({
            "Date": str(s.settlement_date),
            "From (Payer)": payer.display_name if payer else "Unknown",
            "To (Payee)": payee.display_name if payee else "Unknown",
            "Amount (₹)": float(s.amount),
            "Currency": s.currency,
            "Notes": s.notes or "",
            "Source": f"Import" if s.import_session_id else "Manual",
        })

    filename = f"settlements_{group_id[:8]}_{date.today()}"

    if format == "pdf":
        headers = list(rows[0].keys()) if rows else ["No Data"]
        pdf_rows = [[str(r.get(h, "")) for h in headers] for r in rows]
        return _make_pdf_response("Settlement History", headers, pdf_rows, f"{filename}.pdf")

    return _make_csv_response(rows if rows else [{"Message": "No settlements"}], f"{filename}.csv")


# ─── Import Report Export ───


@router.get("/import/{session_id}/export/report")
def export_import_report(
    session_id: str,
    format: str = Query(default="csv", description="csv or pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export an import session report as CSV or PDF."""
    session = db.query(ImportSession).filter(ImportSession.id == session_id).first()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Import session not found")

    anomalies = db.query(ImportAnomaly).filter(
        ImportAnomaly.import_session_id == session_id,
    ).all()

    rows = []
    for a in anomalies:
        rows.append({
            "Type": a.anomaly_type,
            "Severity": a.severity,
            "Description": a.description,
            "Auto-Resolved": "Yes" if a.auto_resolved else "No",
            "Resolution": a.auto_resolution or ("User reviewed" if a.resolution else "Pending"),
            "Requires Action": "Yes" if a.requires_user_action else "No",
        })

    # Add summary row
    summary = {
        "Type": "SUMMARY",
        "Severity": "",
        "Description": (
            f"Total Rows: {session.total_rows} | "
            f"Imported: {session.imported_expenses} expenses, {session.imported_settlements} settlements | "
            f"Skipped: {session.skipped_rows} | "
            f"Anomalies: {session.detected_anomalies}"
        ),
        "Auto-Resolved": "",
        "Resolution": "",
        "Requires Action": "",
    }

    filename = f"import_report_{session_id[:8]}_{date.today()}"

    if format == "pdf":
        headers = list(rows[0].keys()) if rows else ["No Data"]
        pdf_rows = [[str(r.get(h, "")) for h in headers] for r in rows]
        pdf_rows.append([str(summary.get(h, "")) for h in headers])
        return _make_pdf_response(
            f"Import Report — {session.file_name}", headers, pdf_rows, f"{filename}.pdf"
        )

    rows.append(summary)
    return _make_csv_response(rows if rows else [{"Message": "No anomalies"}], f"{filename}.csv")
