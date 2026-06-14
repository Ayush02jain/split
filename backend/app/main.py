from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, SessionLocal, Base

# Import all models so Base.metadata knows about them
from app.models.user import User
from app.models.group import Group, GroupMembership
from app.models.expense import Expense, ExpenseParticipant, ExpenseCategory
from app.models.settlement import Settlement
from app.models.import_session import (
    ImportSession, ImportedRecord, ImportAnomaly, ImportConflictResolution,
)
from app.models.audit import CurrencyRate, AuditLog

# Import routers
from app.api.auth import router as auth_router
from app.api.groups import router as groups_router
from app.api.expenses import router as expenses_router
from app.api.settlements import router as settlements_router
from app.api.csv_import import router as csv_import_router
from app.api.analytics import router as analytics_router
from app.api.export import router as export_router


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


def _seed_defaults():
    """Seed default expense categories on first startup."""
    db = SessionLocal()
    try:
        existing = db.query(ExpenseCategory).filter(ExpenseCategory.is_default == True).count()
        if existing == 0:
            for cat in DEFAULT_CATEGORIES:
                db.add(ExpenseCategory(name=cat["name"], icon=cat["icon"], is_default=True))
            db.commit()
            print(f"[OK] Seeded {len(DEFAULT_CATEGORIES)} default categories")
    except Exception as e:
        print(f"Could not seed defaults: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created/verified")
    _seed_defaults()
    yield
    # Shutdown (nothing needed)


app = FastAPI(
    title="Shared Expenses API",
    description="A Splitwise-like shared expenses application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(expenses_router)
app.include_router(settlements_router)
app.include_router(csv_import_router)
app.include_router(analytics_router)
app.include_router(export_router)


@app.get("/")
def root():
    return {"message": "Shared Expenses API is running", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

