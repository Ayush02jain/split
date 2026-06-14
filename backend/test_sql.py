import psycopg2
import os
import json
from urllib.parse import urlparse
from decimal import Decimal

# Handle Decimal serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

url = urlparse('postgresql://neondb_owner:npg_uB8fHizq6YRl@ep-still-dawn-aon6dted.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require')
conn = psycopg2.connect(
    dbname=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port,
    sslmode='require'
)
cursor = conn.cursor()

group_id = '45fab360-a8c4-4f58-ba1a-68bdc705bf01'

cursor.execute('SELECT id, amount, paid_by FROM expenses WHERE group_id = %s', (group_id,))
expenses = cursor.fetchall()

result = {"expenses": [], "participants": []}
for e in expenses:
    result["expenses"].append({"id": e[0], "amount": e[1], "paid_by": e[2]})
    
    cursor.execute('SELECT user_id, share_amount FROM expense_participants WHERE expense_id = %s', (e[0],))
    parts = cursor.fetchall()
    for p in parts:
        result["participants"].append({"expense_id": e[0], "user_id": p[0], "share_amount": p[1]})

with open('db_dump.json', 'w') as f:
    json.dump(result, f, cls=DecimalEncoder, indent=2)

print("Dumped to db_dump.json")
