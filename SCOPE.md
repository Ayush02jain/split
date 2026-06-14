# Project Scope & Database Schema

This document outlines the database schema designed for the application, as well as the Anomaly Log which details every data problem encountered during CSV file imports and how the system handles them.

---

## Database Schema

We chose **PostgreSQL** as our database, accessed via SQLAlchemy in Python. 

### 1. Users Table
Stores information about registered individuals.
- `id`: Primary Key (UUID)
- `email`: String (Unique identifier for login)
- `name`: String (Display name)
- `hashed_password`: String (Securely hashed password)

### 2. Groups Table
Represents a collection of users sharing expenses (e.g., "Apartment 4B" or "Miami Trip").
- `id`: Primary Key (UUID)
- `name`: String
- `description`: String (Optional)
- `created_by_id`: Foreign Key linking to the `Users` table

### 3. Expenses Table
Records a specific transaction paid by one person, meant to be split.
- `id`: Primary Key (UUID)
- `group_id`: Foreign Key linking to `Groups`
- `paid_by_id`: Foreign Key linking to `Users` (The person who paid the bill)
- `amount`: Float (The total cost of the bill)
- `description`: String (e.g., "Dinner at Luigi's")
- `date`: DateTime

### 4. ExpenseParticipants Table
A junction table mapping how a single expense is divided among group members. Instead of saving an array of names, this relational structure allows for uneven splits in the future.
- `id`: Primary Key (UUID)
- `expense_id`: Foreign Key linking to `Expenses`
- `user_id`: Foreign Key linking to `Users`
- `amount_owed`: Float (The exact fraction of the bill this user is responsible for)

---

## CSV Anomaly Log

When a user uploads a CSV file of expenses (for example, migrating data from Splitwise or a bank statement), the data is often messy. 
Our CSV Import Engine scans the file row by row and applies the following anomaly detection and handling rules:

### Anomaly 1: Missing or Empty Names/Descriptions
- **The Problem:** The CSV contains a row where the "Description" or "Paid By" field is completely blank.
- **How We Handled It:** The system rejects the row entirely. It logs an error in the import report: `"Row X skipped: Missing required field 'Description'."` We require these fields to ensure financial records are legally and practically identifiable.

### Anomaly 2: Negative or Zero Amounts
- **The Problem:** The CSV lists an expense as `-50.00` or `0.00` (often seen in bank export refunds).
- **How We Handled It:** Our app only tracks positive debts. If an amount is zero or negative, the row is skipped with the message: `"Row X skipped: Amount must be greater than zero."`

### Anomaly 3: Unrecognized Currency Codes
- **The Problem:** A user uploads a CSV with a column for "Currency" containing `EUR` or `GBP`, but our app currently normalizes everything to a default base currency (e.g., USD/INR).
- **How We Handled It:** Instead of crashing, the system logs a warning in the import report: `"Row X: Converted unrecognized currency 'EUR' to default base currency."` It still imports the expense, but alerts the user that the numerical value was treated as the default currency.

### Anomaly 4: Extra Whitespace
- **The Problem:** Names like `" Alice  "` or `"Bob\n"` cause database mismatches when trying to link the "Paid By" text to an actual User account.
- **How We Handled It:** The system automatically sanitizes the data. It strips leading and trailing whitespaces and removes newline characters before processing. This is handled silently as a data cleaning step.

### Anomaly 5: Unregistered Users in the "Paid By" Column
- **The Problem:** The CSV says "Charlie" paid for dinner, but "Charlie" does not have an account in the system and is not in the group.
- **How We Handled It:** The system cannot attach financial debt to a non-existent entity. The row is skipped with a fatal error: `"Row X skipped: User 'Charlie' not found in group."` The user is forced to add Charlie to the group before re-importing that row.
