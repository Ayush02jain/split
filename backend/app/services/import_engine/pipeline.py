"""
Import Pipeline Orchestrator — The main import engine.

Coordinates all stages of the CSV import:
1. Parse CSV
2. Normalize each row
3. Detect anomalies (per-row and cross-row)
4. Classify anomalies (auto-resolve vs needs-review)
5. Generate preview
6. On user confirmation, commit atomically to database
7. Generate import report
"""
import hashlib
import uuid
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.group import Group, GroupMembership
from app.models.expense import Expense, ExpenseParticipant, ExpenseCategory
from app.models.settlement import Settlement
from app.models.import_session import (
    ImportSession, ImportedRecord, ImportAnomaly, ImportConflictResolution,
    ImportStatus, RecordStatus, ResultType, AnomalySeverity,
)
from app.models.audit import AuditLog, CurrencyRate
from app.services.import_engine.parser import parse_csv
from app.services.import_engine.normalizer import normalize_row
from app.services.import_engine.anomaly_detector import (
    detect_settlement, find_duplicates, validate_membership,
)
from app.services.balance import round_money, calculate_shares
from app.config import settings


class ImportPipeline:
    """
    Orchestrates the full CSV import process.
    
    Usage:
        pipeline = ImportPipeline(db, group_id, user_id)
        session = pipeline.process_file(file_content, file_name)
        # session now contains preview data
        # After user reviews and resolves conflicts:
        pipeline.commit_import(session.id)
    """

    def __init__(self, db: Session, group_id: str, user_id: str):
        self.db = db
        self.group_id = group_id
        self.user_id = user_id
        self.known_users = self._load_known_users()
        self.memberships = self._load_memberships()
        self.group = db.query(Group).filter(Group.id == group_id).first()

    def _load_known_users(self) -> List[str]:
        """Load display names of all known users."""
        users = self.db.query(User).all()
        return [u.display_name for u in users]

    def _load_memberships(self) -> Dict[str, Dict]:
        """Load membership dates for all group members."""
        memberships = self.db.query(GroupMembership).filter(
            GroupMembership.group_id == self.group_id
        ).all()
        result = {}
        for m in memberships:
            user = self.db.query(User).filter(User.id == m.user_id).first()
            if user:
                result[user.display_name] = {
                    "user_id": user.id,
                    "joined_at": m.joined_at,
                    "left_at": m.left_at,
                }
        return result

    def _find_user_by_name(self, name: str) -> Optional[User]:
        """Find a user by display name (case-insensitive)."""
        return self.db.query(User).filter(
            User.display_name.ilike(name)
        ).first()

    def _get_or_create_user(self, name: str) -> User:
        """Find existing user or create a placeholder."""
        user = self._find_user_by_name(name)
        if user:
            return user

        # Create placeholder user
        user = User(
            email=f"{name.lower().replace(' ', '.')}@placeholder.local",
            display_name=name,
            password_hash="placeholder_no_login",
            is_placeholder=True,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def process_file(self, file_content: str, file_name: str) -> ImportSession:
        """
        Process the CSV file through the full pipeline.
        Creates the import session and all related records.
        Does NOT commit expenses/settlements yet — that happens in commit_import().
        """
        # Stage 1-2: Create import session
        file_hash = hashlib.sha256(file_content.encode()).hexdigest()

        # Check for duplicate import
        existing = self.db.query(ImportSession).filter(
            ImportSession.file_hash == file_hash,
            ImportSession.group_id == self.group_id,
            ImportSession.status.in_(["completed", "completed_with_warnings"]),
        ).first()

        session = ImportSession(
            group_id=self.group_id,
            initiated_by=self.user_id,
            file_name=file_name,
            file_hash=file_hash,
            status=ImportStatus.PROCESSING.value,
            started_at=datetime.utcnow(),
        )
        self.db.add(session)
        self.db.flush()

        if existing:
            anomaly = ImportAnomaly(
                import_session_id=session.id,
                anomaly_type="duplicate_import",
                severity=AnomalySeverity.WARNING.value,
                description=f"This file was previously imported (session {existing.id[:8]}). Proceeding may create duplicates.",
                auto_resolved=False,
                requires_user_action=True,
            )
            self.db.add(anomaly)

        # Stage 3: Parse CSV
        rows, parse_errors = parse_csv(file_content)
        if parse_errors:
            session.status = ImportStatus.FAILED.value
            for err in parse_errors:
                anomaly = ImportAnomaly(
                    import_session_id=session.id,
                    anomaly_type="parse_error",
                    severity=AnomalySeverity.CRITICAL.value,
                    description=err,
                    auto_resolved=False,
                    requires_user_action=False,
                )
                self.db.add(anomaly)
            self.db.commit()
            return session

        session.total_rows = len(rows)

        # Stages 4-5: Normalize each row and collect per-row anomalies
        normalized_rows = []
        all_records = []

        for raw_row in rows:
            row_num = raw_row.get("_row_number", 0)

            # Create imported record
            record = ImportedRecord(
                import_session_id=session.id,
                row_number=row_num,
                raw_data=raw_row,
                status=RecordStatus.VALID.value,
            )
            self.db.add(record)
            self.db.flush()

            # Normalize
            normalized, row_anomalies = normalize_row(raw_row, self.known_users)
            record.normalized_data = normalized
            normalized["_record_id"] = record.id
            normalized["_row_number"] = row_num

            # Store per-row anomalies
            has_error = False
            for a in row_anomalies:
                anomaly = ImportAnomaly(
                    import_session_id=session.id,
                    imported_record_id=record.id,
                    anomaly_type=a["type"],
                    severity=a.get("severity", "warning"),
                    description=a["description"],
                    auto_resolved=a.get("auto_resolved", False),
                    auto_resolution=a.get("auto_resolution"),
                    requires_user_action=a.get("requires_user_action", False),
                )
                self.db.add(anomaly)
                if a.get("severity") == "error" and not a.get("auto_resolved"):
                    has_error = True

            if has_error:
                record.status = RecordStatus.ERROR.value

            normalized_rows.append(normalized)
            all_records.append(record)

        # Stage 6: Cross-row anomaly detection

        # Settlement detection
        for i, norm_row in enumerate(normalized_rows):
            is_settlement, reason = detect_settlement(norm_row)
            if is_settlement:
                record = all_records[i]
                anomaly = ImportAnomaly(
                    import_session_id=session.id,
                    imported_record_id=record.id,
                    anomaly_type="settlement_as_expense",
                    severity=AnomalySeverity.WARNING.value,
                    description=f"Row {norm_row['_row_number']} appears to be a settlement, not an expense: {reason}",
                    auto_resolved=False,
                    requires_user_action=True,
                )
                self.db.add(anomaly)
                record.status = RecordStatus.PENDING_REVIEW.value

        # Duplicate detection
        duplicate_anomalies = find_duplicates(normalized_rows)
        for dup in duplicate_anomalies:
            row_nums = dup.get("row_numbers", [])
            related_record_ids = []
            for rn in row_nums:
                for rec in all_records:
                    if rec.row_number == rn:
                        related_record_ids.append(rec.id)
                        rec.status = RecordStatus.PENDING_REVIEW.value

            anomaly = ImportAnomaly(
                import_session_id=session.id,
                imported_record_id=related_record_ids[0] if related_record_ids else None,
                anomaly_type=dup["type"],
                severity=dup["severity"],
                description=dup["description"],
                auto_resolved=False,
                requires_user_action=True,
                related_record_ids={"record_ids": related_record_ids, "row_numbers": row_nums},
            )
            self.db.add(anomaly)

        # Membership validation
        for i, norm_row in enumerate(normalized_rows):
            membership_anomalies = validate_membership(
                norm_row, self.memberships,
                group_created_at=self.group.created_at.date() if self.group else None,
            )
            for ma in membership_anomalies:
                anomaly = ImportAnomaly(
                    import_session_id=session.id,
                    imported_record_id=all_records[i].id,
                    anomaly_type=ma["type"],
                    severity=ma.get("severity", "info"),
                    description=ma["description"],
                    auto_resolved=ma.get("auto_resolved", False),
                    auto_resolution=ma.get("auto_resolution"),
                    requires_user_action=ma.get("requires_user_action", False),
                )
                self.db.add(anomaly)

        # Update session statistics
        all_anomalies = self.db.query(ImportAnomaly).filter(
            ImportAnomaly.import_session_id == session.id
        ).all()

        session.detected_anomalies = len(all_anomalies)
        session.pending_reviews = len([a for a in all_anomalies if a.requires_user_action and not a.auto_resolved])
        session.skipped_rows = len([r for r in all_records if r.status == RecordStatus.ERROR.value])

        if session.pending_reviews > 0:
            session.status = ImportStatus.AWAITING_REVIEW.value
        else:
            session.status = ImportStatus.AWAITING_REVIEW.value  # Always allow user to review before commit

        self.db.commit()
        return session

    def commit_import(self, session_id: str) -> ImportSession:
        """
        Commit the import — create actual Expense and Settlement records.
        This is called after user has reviewed and resolved all conflicts.
        Wraps everything in a transaction for atomicity.
        """
        session = self.db.query(ImportSession).filter(ImportSession.id == session_id).first()
        if not session:
            raise ValueError("Import session not found")

        records = self.db.query(ImportedRecord).filter(
            ImportedRecord.import_session_id == session_id,
        ).order_by(ImportedRecord.row_number).all()

        expenses_created = 0
        settlements_created = 0
        skipped = 0

        try:
            for record in records:
                if record.status in (RecordStatus.ERROR.value, RecordStatus.SKIPPED.value):
                    skipped += 1
                    continue

                # Check if this record has unresolved required-action anomalies
                unresolved = self.db.query(ImportAnomaly).filter(
                    ImportAnomaly.imported_record_id == record.id,
                    ImportAnomaly.requires_user_action == True,
                    ImportAnomaly.auto_resolved == False,
                ).all()

                # Check resolutions
                all_resolved = True
                skip_this = False
                convert_to_settlement = False

                for anomaly in unresolved:
                    resolution = self.db.query(ImportConflictResolution).filter(
                        ImportConflictResolution.anomaly_id == anomaly.id
                    ).first()
                    if not resolution:
                        all_resolved = False
                        break
                    if resolution.action == "skip":
                        skip_this = True
                    elif resolution.action == "convert_to_settlement":
                        convert_to_settlement = True

                if not all_resolved:
                    record.status = RecordStatus.PENDING_REVIEW.value
                    continue

                if skip_this:
                    record.status = RecordStatus.SKIPPED.value
                    record.result_type = ResultType.SKIPPED.value
                    skipped += 1
                    continue

                norm = record.normalized_data or {}

                # Check if this should be a settlement
                is_settlement_row, _ = detect_settlement(norm)
                if convert_to_settlement or (is_settlement_row and self._has_resolution_action(record.id, "convert_to_settlement")):
                    settlement = self._create_settlement_from_row(norm, session)
                    if settlement:
                        record.status = RecordStatus.IMPORTED.value
                        record.result_type = ResultType.SETTLEMENT.value
                        record.result_id = settlement.id
                        settlements_created += 1
                    else:
                        record.status = RecordStatus.ERROR.value
                        record.error_message = "Failed to create settlement"
                        skipped += 1
                    continue

                # Create expense
                expense = self._create_expense_from_row(norm, session)
                if expense:
                    record.status = RecordStatus.IMPORTED.value
                    record.result_type = ResultType.EXPENSE.value
                    record.result_id = expense.id
                    expenses_created += 1
                else:
                    record.status = RecordStatus.ERROR.value
                    record.error_message = "Failed to create expense — missing required data"
                    skipped += 1

            # Update session
            session.imported_expenses = expenses_created
            session.imported_settlements = settlements_created
            session.skipped_rows = skipped
            session.status = ImportStatus.COMPLETED.value if skipped == 0 else ImportStatus.COMPLETED_WITH_WARNINGS.value
            session.completed_at = datetime.utcnow()

            # Audit log
            audit = AuditLog(
                user_id=self.user_id,
                action="import_completed",
                entity_type="ImportSession",
                entity_id=session.id,
                details={
                    "expenses": expenses_created,
                    "settlements": settlements_created,
                    "skipped": skipped,
                },
            )
            self.db.add(audit)

            self.db.commit()
            return session

        except Exception as e:
            self.db.rollback()
            session.status = ImportStatus.FAILED.value
            session.completed_at = datetime.utcnow()
            self.db.commit()
            raise e

    def _has_resolution_action(self, record_id: str, action: str) -> bool:
        """Check if any anomaly for this record has a specific resolution action."""
        anomalies = self.db.query(ImportAnomaly).filter(
            ImportAnomaly.imported_record_id == record_id,
        ).all()
        for a in anomalies:
            if a.resolution and a.resolution.action == action:
                return True
        return False

    def _create_expense_from_row(self, norm: Dict, session: ImportSession) -> Optional[Expense]:
        """Create an Expense record from normalized row data."""
        if not norm.get("date") or not norm.get("amount") or not norm.get("paid_by"):
            return None

        amount = Decimal(str(norm["amount"]))
        currency = norm.get("currency", "INR")

        # Handle negative amounts as refunds (store as positive with negative participant shares)
        is_refund = amount < 0
        if is_refund:
            amount = abs(amount)

        # Currency conversion
        converted_amount = None
        exchange_rate = None
        if currency == "USD":
            exchange_rate = Decimal(str(settings.USD_TO_INR_RATE))
            converted_amount = round_money(amount * exchange_rate)

        # Find or create payer
        payer = self._get_or_create_user(norm["paid_by"])

        # Auto-categorize
        category_id = self._auto_categorize(norm.get("description", ""))

        expense = Expense(
            group_id=self.group_id,
            title=norm.get("description", "Imported expense"),
            description=norm.get("notes", ""),
            amount=amount,
            currency=currency,
            converted_amount=converted_amount,
            exchange_rate=exchange_rate,
            paid_by=payer.id,
            split_type=norm.get("split_type", "equal"),
            expense_date=datetime.strptime(norm["date"], "%Y-%m-%d").date(),
            category_id=category_id,
            import_session_id=session.id,
            source_row_number=norm.get("_row_number"),
        )
        self.db.add(expense)
        self.db.flush()

        # Create participants
        effective_amount = converted_amount if converted_amount else amount
        participants = norm.get("participants", [])
        split_type = norm.get("split_type", "equal")
        split_details = norm.get("split_details", [])

        # Filter out inactive members
        active_participants = []
        expense_date = datetime.strptime(norm["date"], "%Y-%m-%d").date()
        for p_name in participants:
            if p_name in self.memberships:
                m = self.memberships[p_name]
                if m["joined_at"] and expense_date < m["joined_at"]:
                    continue
                if m["left_at"] and expense_date > m["left_at"]:
                    continue
            active_participants.append(p_name)

        if not active_participants:
            active_participants = participants  # fallback

        if split_type == "equal" or not split_details:
            # Equal split among active participants
            participant_ids = []
            for p_name in active_participants:
                user = self._get_or_create_user(p_name)
                participant_ids.append(user.id)

            shares = calculate_shares(effective_amount, "equal", participant_ids)

            for uid, share_amt in shares.items():
                if is_refund:
                    share_amt = -share_amt
                ep = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=uid,
                    share_amount=share_amt,
                )
                self.db.add(ep)

        elif split_type == "percentage":
            for detail in split_details:
                user = self._get_or_create_user(detail["name"])
                if user.display_name not in [p for p in active_participants]:
                    continue
                pct = Decimal(str(detail["value"]))
                share_amt = round_money(effective_amount * pct / Decimal("100"))
                if is_refund:
                    share_amt = -share_amt
                ep = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=user.id,
                    share_amount=share_amt,
                    share_percentage=pct,
                )
                self.db.add(ep)

        elif split_type == "unequal":
            for detail in split_details:
                user = self._get_or_create_user(detail["name"])
                share_amt = round_money(Decimal(str(detail["value"])))
                if is_refund:
                    share_amt = -share_amt
                ep = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=user.id,
                    share_amount=share_amt,
                )
                self.db.add(ep)

        elif split_type == "share":
            total_units = sum(d.get("value", 1) for d in split_details)
            for detail in split_details:
                user = self._get_or_create_user(detail["name"])
                if user.display_name not in [p for p in active_participants]:
                    continue
                units = detail.get("value", 1)
                share_amt = round_money(effective_amount * Decimal(str(units)) / Decimal(str(total_units)))
                if is_refund:
                    share_amt = -share_amt
                ep = ExpenseParticipant(
                    expense_id=expense.id,
                    user_id=user.id,
                    share_amount=share_amt,
                    share_units=int(units),
                )
                self.db.add(ep)

        self.db.flush()
        return expense

    def _create_settlement_from_row(self, norm: Dict, session: ImportSession) -> Optional[Settlement]:
        """Create a Settlement record from a normalized row."""
        if not norm.get("paid_by") or not norm.get("amount"):
            return None

        payer = self._get_or_create_user(norm["paid_by"])
        participants = norm.get("participants", [])

        # The payee is the participant (in a 1:1 settlement)
        payee_name = None
        for p in participants:
            if p.lower() != norm["paid_by"].lower():
                payee_name = p
                break

        if not payee_name and participants:
            payee_name = participants[0]

        if not payee_name:
            return None

        payee = self._get_or_create_user(payee_name)

        settlement = Settlement(
            group_id=self.group_id,
            payer_id=payer.id,
            payee_id=payee.id,
            amount=abs(Decimal(str(norm["amount"]))),
            currency=norm.get("currency", "INR"),
            settlement_date=datetime.strptime(norm["date"], "%Y-%m-%d").date() if norm.get("date") else date.today(),
            notes=norm.get("notes", ""),
            import_session_id=session.id,
            source_row_number=norm.get("_row_number"),
        )
        self.db.add(settlement)
        self.db.flush()

        # Ensure both users are group members
        self._ensure_group_membership(payer, settlement.settlement_date)
        self._ensure_group_membership(payee, settlement.settlement_date)

        return settlement

    def _ensure_group_membership(self, user: User, ref_date: date):
        """Ensure a user is a member of the group (create membership if not)."""
        existing = self.db.query(GroupMembership).filter(
            GroupMembership.group_id == self.group_id,
            GroupMembership.user_id == user.id,
        ).first()
        if not existing:
            membership = GroupMembership(
                group_id=self.group_id,
                user_id=user.id,
                role="member",
                joined_at=ref_date,
            )
            self.db.add(membership)
            self.db.flush()

    def _auto_categorize(self, description: str) -> Optional[str]:
        """Auto-categorize expense by keyword matching."""
        desc_lower = description.lower()
        category_keywords = {
            "Rent": ["rent"],
            "Utilities": ["electricity", "wifi", "water", "gas", "cylinder"],
            "Food & Groceries": ["groceries", "bigbasket", "dmart", "grocery"],
            "Travel": ["flight", "cab", "taxi", "uber", "airport", "scooter"],
            "Entertainment": ["movie", "parasailing", "drinks", "party"],
            "Household": ["cleaning", "maid", "furniture", "deep clean"],
            "Dining": ["dinner", "lunch", "brunch", "pizza", "snacks", "swiggy", "restaurant", "shack"],
        }

        for cat_name, keywords in category_keywords.items():
            for kw in keywords:
                if kw in desc_lower:
                    cat = self.db.query(ExpenseCategory).filter(
                        ExpenseCategory.name == cat_name,
                    ).first()
                    if cat:
                        return cat.id
                    break

        return None
