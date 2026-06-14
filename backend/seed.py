"""
Seed script — populates the database with default data.

Run: python seed.py
"""
import sys
import os

# Ensure we can import from the app package
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, SessionLocal, Base
from app.models.user import User
from app.models.group import Group, GroupMembership
from app.models.expense import Expense, ExpenseParticipant, ExpenseCategory
from app.models.settlement import Settlement
from app.models.import_session import (
    ImportSession, ImportedRecord, ImportAnomaly, ImportConflictResolution,
)
from app.models.audit import CurrencyRate, AuditLog


DEFAULT_CATEGORIES = [
    {"name": "Rent", "icon": "🏠"},
    {"name": "Utilities", "icon": "💡"},
    {"name": "Food & Groceries", "icon": "🛒"},
    {"name": "Dining", "icon": "🍽️"},
    {"name": "Travel", "icon": "✈️"},
    {"name": "Entertainment", "icon": "🎬"},
    {"name": "Shopping", "icon": "🛍️"},
    {"name": "Household", "icon": "🧹"},
    {"name": "Miscellaneous", "icon": "📦"},
]

DEFAULT_CURRENCY_RATES = [
    {"from_currency": "USD", "to_currency": "INR", "rate": 85.0, "source": "manual_config"},
]


def seed_categories(db):
    """Create default expense categories if they don't exist."""
    existing = db.query(ExpenseCategory).filter(ExpenseCategory.is_default == True).count()
    if existing > 0:
        print(f"  ⏭️  {existing} default categories already exist, skipping.")
        return

    for cat in DEFAULT_CATEGORIES:
        category = ExpenseCategory(
            name=cat["name"],
            icon=cat["icon"],
            is_default=True,
            group_id=None,  # Global categories
        )
        db.add(category)

    db.commit()
    print(f"  ✅ Created {len(DEFAULT_CATEGORIES)} default categories.")


def seed_currency_rates(db):
    """Create default currency exchange rates if they don't exist."""
    from datetime import date

    existing = db.query(CurrencyRate).count()
    if existing > 0:
        print(f"  ⏭️  {existing} currency rates already exist, skipping.")
        return

    for rate in DEFAULT_CURRENCY_RATES:
        cr = CurrencyRate(
            from_currency=rate["from_currency"],
            to_currency=rate["to_currency"],
            rate=rate["rate"],
            effective_date=date.today(),
            source=rate["source"],
        )
        db.add(cr)

    db.commit()
    print(f"  ✅ Created {len(DEFAULT_CURRENCY_RATES)} currency rates.")


def main():
    print("🌱 Seeding database...")
    print()

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("  ✅ Database tables created/verified.")

    db = SessionLocal()
    try:
        seed_categories(db)
        seed_currency_rates(db)
        print()
        print("🎉 Seeding complete!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
