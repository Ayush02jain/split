from app.database import SessionLocal
from app.models.user import User
from app.models.group import Group, GroupMembership
from app.models.expense import Expense, ExpenseParticipant, ExpenseCategory
from app.models.settlement import Settlement

db = SessionLocal()
group_id = "45fab360-a8c4-4f58-ba1a-68bdc705bf01"

print("--- EXPENSES ---")
expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
for e in expenses:
    print(f"Expense {e.id}: {e.amount} paid by {e.paid_by}")
    parts = db.query(ExpenseParticipant).filter(ExpenseParticipant.expense_id == e.id).all()
    for p in parts:
        print(f"  Participant {p.user_id}: {p.share_amount}")

print("--- ALL EXPENSES ANY GROUP ---")
all_exp = db.query(Expense).all()
for e in all_exp:
    print(f"Group {e.group_id} - Expense {e.id}")
