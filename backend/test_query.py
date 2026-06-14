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
    for p in e.participants:
        print(f"  Participant {p.user_id}: {p.share_amount}")

from app.services.balance import compute_group_balances
print("--- BALANCES ---")
print(compute_group_balances(db, group_id))
