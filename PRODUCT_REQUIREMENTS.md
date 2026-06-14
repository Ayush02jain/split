# PRODUCT_REQUIREMENTS.md

# Shared Expenses App — Product Requirements & CSV Import Specification

## 1. Overview

This project is a Splitwise-like Shared Expenses Application designed for a group of flatmates. The application allows users to create groups, manage members, record shared expenses, settle debts, and import historical transaction data from a CSV file.

The core challenge of the project is not only to build the expense tracker, but also to handle messy real-world data through a robust CSV import pipeline that can detect, surface, and resolve inconsistencies without silently modifying data.

---

# 2. Product Goals

The application should:

* Provide an intuitive way to track shared expenses.
* Maintain accurate balances between members.
* Support members joining and leaving groups over time.
* Allow debt settlement and payment recording.
* Import historical expenses from a CSV file.
* Detect and report anomalies during import.
* Provide transparency and traceability for every balance calculation.

---

# 3. Core Features

## 3.1 Authentication

* User registration.
* User login/logout.
* Session management.
* Protected routes for authenticated users.

---

## 3.2 Group Management

Users should be able to:

* Create a group.
* View all groups they belong to.
* Add members to a group.
* Remove members from a group.
* Record membership start and end dates.

### Group Membership Rules

* A member can join after the group has already been created.
* A member can leave the group.
* Expenses should only affect members who were active on the expense date.
* Historical expenses should remain unchanged when membership changes.

### Example

| Member | Joined | Left   |
| ------ | ------ | ------ |
| Aisha  | Feb 1  | Active |
| Meera  | Feb 1  | Mar 31 |
| Sam    | Apr 15 | Active |

If an expense occurs on April 20, Meera should not be included in the split.

---

## 3.3 Expense Management

Users should be able to:

* Add an expense manually.
* Edit an expense.
* Delete an expense.
* View expense history.
* Attach notes or descriptions.
* Select expense date.
* Select payer.
* Select participants.
* Choose split type.

### Supported Split Types

The application must support every split type encountered in the provided CSV. Typical split types include:

* Equal split.
* Exact amount split.
* Percentage split.
* Share/unit-based split.
* Unequal custom split.

### Expense Information

Each expense should contain:

* Expense title.
* Amount.
* Currency.
* Paid by.
* Participants.
* Split type.
* Date.
* Optional notes.
* Import source metadata (if imported).

---

## 3.4 Balance Calculation

The system should automatically compute:

* Group-wise balances.
* User-wise balances.
* Net amount owed by or owed to each member.

### Individual Summary

Example:

* You owe Rohan: ₹500
* Priya owes you: ₹300

### Group Summary

Example:

* Aisha should receive ₹1,000.
* Sam owes ₹600.
* Rohan owes ₹400.

---

## 3.5 Expense Traceability

Every computed balance should be explainable.

A user should be able to view:

* Which expenses contributed to their balance?
* How the final payable/receivable amount was calculated.
* Which imported records were included?

This addresses the requirement that users should never see unexplained "magic numbers."

---

## 3.6 Settlement Management

The application should support debt settlement.

Users should be able to:

* Record a payment from one member to another.
* Mark balances as partially or fully settled.
* View settlement history.

A settlement should reduce outstanding balances without deleting original expenses.

Example:

* Aisha owes Rohan ₹500.
* Aisha pays Rohan ₹500.
* A settlement record is created.
* Outstanding balance becomes ₹0.

---


## 3.7 Expense Categories & Analytics

The application should support categorizing expenses to improve organization and reporting.

### Supported Categories (configurable)

* Rent
* Utilities
* Food & Groceries
* Travel
* Entertainment
* Shopping
* Miscellaneous

### Analytics Dashboard

Users should be able to:
* View total spending by category.
* View spending trends over time.
* View member-wise contribution summaries.
* View monthly and weekly expense breakdowns.
* Filter expenses by category, date range, and group.

Expense categories should also be preserved during CSV imports whenever category information can be inferred or is explicitly available.

---

## 3.8 Export & Reporting

The application should provide export capabilities for both operational and auditing purposes.

Users should be able to export:
* Group expense history.
* Individual balance summaries.
* Settlement history.
* CSV import reports.
* Analytics summaries.

### Supported Export Formats

* CSV
* PDF

Exported reports should preserve important metadata such as dates, currencies, categories, and import source information where applicable.

---

## 3.9 Role-Based Permissions

The system should support basic role-based access control within a group.

### Roles

### Admin
* Create and delete groups.
* Add or remove group members.
* Initiate CSV imports.
* Approve or reject import conflicts.
* Manage duplicate resolution workflows.
* Export group reports.

### Member
* View group expenses and balances.
* Add manual expenses.
* Record settlements.
* View import reports.
* Suggest resolutions for import conflicts (optional).

Role separation ensures that historical data imports and conflict resolutions are controlled and auditable.

---


# 4. CSV Import Module

## 4.1 Purpose

The CSV importer is responsible for importing the provided historical spreadsheet exactly as supplied.

The file must NOT be edited manually before upload.

The importer should:

1. Read the file.
2. Parse every row.
3. Validate the data.
4. Detect anomalies.
5. Present anomalies to the user.
6. Apply a documented handling policy.
7. Store valid data.
8. Generate an import report.

---

## 4.2 Import Workflow

## 4.2 Import Workflow

```text
             Upload CSV
                  │
                  ▼
        Create Import Session
                  │
                  ▼
         Parse & Validate File
                  │
                  ▼
        Row-by-Row Normalization
                  │
                  ▼
        Anomaly Detection Engine
                  │
                  ▼
         Conflict Resolution Stage
                  │
      ┌───────────┴───────────┐
      │                       │
Auto-resolvable        Needs User Review
      │                       │
      └───────────┬───────────┘
                  ▼
          Generate Preview
                  │
                  ▼
           User Confirms
                  │
                  ▼
         Atomic Database Import
                  │
                  ▼
          Generate Import Report
```

---

## 4.3 Import Session Management

CSV imports should be treated as independent import sessions rather than one-time upload actions.

Each import session should maintain:
* Unique import session ID.
* File name.
* Upload timestamp.
* Import status.
* Number of processed rows.
* Number of imported expenses.
* Number of detected anomalies.
* Number of pending manual reviews.
* User who initiated the import.

Every imported record and every anomaly should be linked back to its import session to provide complete traceability and auditability.

The system should also maintain an Import History page where users can:
* View previous imports.
* Download import reports.
* Review unresolved conflicts.
* View duplicate detection decisions.
* Track failed or partially completed imports.

---

# 5. CSV Import Features

## 5.1 Automatic Member Mapping

* Match names from CSV with existing users.
* Create new placeholder users if necessary.
* Allow manual mapping if duplicate names exist.

## 5.2 Automatic Expense Creation

* Convert valid expense rows into expense records.

## 5.3 Settlement Detection

* Detect rows that represent payments instead of expenses.
* Convert them into settlement records if applicable.

## 5.4 Currency Handling

* Detect expense currency.
* Support INR and USD.
* Convert foreign currency using a documented exchange-rate policy.
* Preserve the original amount and original currency for auditing.

## 5.5 Duplicate Detection

* Identify potential duplicate expenses.
* Allow user approval before deleting or merging duplicates.

## 5.6 Import Report Generation

Generate a report containing:

* Total rows processed.
* Expenses imported.
* Settlements imported.
* Duplicate entries detected.
* Currency conversions performed.
* Invalid rows skipped.
* User actions required.

## 5.7 Import Preview

Before committing any data to the database, the application should generate an import preview summarizing:
* Valid expenses.
* Potential duplicates.
* Settlement records detected.
* Unknown users.
* Currency conversions.
* Rows requiring manual review.

Users should be able to review and approve the import before finalizing it.

---

## 5.8 Import History & Audit Trail

The application should maintain a complete history of all CSV imports.

For every import, the system should store:
* Original file name.
* Import timestamp.
* Import status.
* Number of records processed.
* Detected anomalies.
* User actions taken during conflict resolution.

No imported data should be silently modified or discarded without leaving an audit trail.

---

## 5.9 AI-Assisted Duplicate Detection

As an enhancement, the importer may use AI-assisted or similarity-based techniques to identify duplicate expenses.

Potential duplicate scoring may consider:
* Same payer.
* Same amount.
* Same date.
* Same participants.
* Similar expense descriptions.

The AI engine should only provide suggestions. Final decisions should always require user approval for ambiguous cases.

---

# 6. CSV Import Edge Cases & Conflict Handling

## 6.1 Duplicate Expense Entries

### Example

Two identical dinner expenses appear twice.

**Possible policy:**

* Flag as potential duplicate.
* Ask user for confirmation before removal.

---

## 6.2 Similar Expenses With Different Amounts

### Example

* Dinner — ₹1200
* Dinner — ₹1250

Same date and participants but different amount.

**Policy:**

* Mark as conflict.
* Require manual review.

---

## 6.3 Settlement Recorded as Expense

A payment between two members is mistakenly logged as an expense.

**Policy:**

* Detect using keywords/rules.
* Convert to settlement or request confirmation.

---

## 6.4 Negative Amount

Example:

* Amount = -₹500

Possible interpretations:

* Refund.
* Correction.
* Invalid entry.

**Policy:**

* Flag for review.
* Optionally treat as refund.

---

## 6.5 Missing Required Fields

Missing:

* Amount.
* Payer.
* Date.
* Participants.

**Policy:**

* Skip import for that row.
* Log error in import report.

---

## 6.6 Invalid Numeric Format

Examples:

* ₹1,2OO (contains letter O).
* "one thousand".

**Policy:**

* Validation error.
* Require correction.

---

## 6.7 Invalid Date Format

Examples:

* 32/04/2025
* Empty date field.

**Policy:**

* Reject row and report issue.

---

## 6.8 Future-Dated Expense

The expense date is after the current date.

**Policy:**

* Warn user.
* Allow import after confirmation.

---

## 6.9 Expense Before User Joined Group

Example:
Sam joined on April 15, but the expense date is March 20.

**Policy:**

* Exclude Sam from the split.
* Log decision in import report.

---

## 6.10 Expense After User Left Group

Example:
Meera left on March 31, but the expense date is April 12.

**Policy:**

* Exclude Meera automatically.
* Record exclusion in audit log.

---

## 6.11 Unknown User Name

CSV contains a member not present in the system.

**Policy:**

* Create placeholder member.
* Ask user to map or confirm.

---

## 6.12 Currency Mismatch

Trip expenses are stored in USD, while the rest are INR.

**Policy:**

* Detect currency.
* Convert according to the configured exchange rate.
* Store original value.

---

## 6.13 Empty CSV File

**Policy:**

* Abort import gracefully.
* Display a user-friendly error.

---

## 6.14 Corrupted CSV Structure

Examples:

* Missing columns.
* Unexpected delimiter.
* Broken quotes.

**Policy:**

* Reject import.
* Display parsing errors.

---

## 6.15 Unsupported Split Type

CSV contains a split mechanism not yet implemented.

**Policy:**

* Flag row.
* Skip import for the affected record.
* Include in anomaly report.

---

## 6.16 Multiple Possible Duplicates

One expense matches multiple existing records.

**Policy:**

* Show all candidate matches.
* Let the user decide.

---

## 6.17 Floating Point / Rounding Errors

Currency conversion or percentage splits may produce decimals.

**Policy:**

* Use fixed decimal precision.
* Apply the documented rounding rule consistently.

---

## 6.18 Importing Same CSV Multiple Times

User accidentally uploads the same file again.

**Policy Options:**

* Detect previously imported rows.
* Warn user.
* Prevent duplicate insertion unless explicitly confirmed.

---

## 6.19 Expense Amount Does Not Match Split Totals

The total expense amount differs from the sum of participant splits.

**Policy:**
* Flag the inconsistency.
* Require manual review before import.

---

## 6.20 Invalid Percentage Split

The total percentage allocation does not equal 100%.

**Policy:**
* Reject the record.
* Add it to the anomaly report.

---

## 6.21 Expense References Non-Group Member

The imported expense includes a participant who is not currently associated with the target group.

**Policy:**
* Create placeholder mapping or require user assignment.
* Log the event for review.

---

## 6.22 Expense Before Group Creation

The expense date predates the creation date of the target group.

**Policy:**
* Flag for review.
* Allow import only after user confirmation.

---

## 6.23 Settlement Amount Exceeds Outstanding Balance

A settlement row attempts to settle more money than is currently owed.

**Policy:**
* Flag the record.
* Require manual verification.

---

## 6.24 Duplicate CSV Import

A user uploads a file that has already been imported previously.

**Policy:**
* Detect matching import signatures.
* Warn the user.
* Prevent accidental duplicate imports unless explicitly confirmed.

---

## 6.25 Ambiguous User Mapping

Multiple existing users could match a single imported user name.

**Policy:**
* Present all candidate matches.
* Require the user to select the correct mapping.

---

## 6.26 Missing or Unsupported Currency

The currency field is empty or contains an unsupported value.

**Policy:**
* Flag the row.
* Request manual selection of the currency before import.

---

# 7. User Approval Workflow

Certain anomalies should never be resolved automatically.

Require user confirmation for:

* Duplicate deletion.
* Record merging.
* Ambiguous member mapping.
* Settlement conversion.
* Conflicting duplicate amounts.
* Unknown currencies.

---

# 8. Non-Functional Requirements

## Performance

* Import should handle large CSV files efficiently.
* Balance calculation should remain responsive.

## Reliability

* Partial import failures should not corrupt the database.
* Use transactions where possible.

## Auditability

* Every imported row should have an import status.
* Every automatic decision should be logged.

## Transparency

* Users should always understand why a balance exists.
* Import decisions should be visible in the generated report.

---

# 9. Suggested Database Entities

* User
* Group
* GroupMembership
* Expense
* ExpenseParticipant
* ExpenseCategory
* Settlement
* ImportSession
* ImportedRecord
* ImportAnomaly
* ImportConflictResolution
* CurrencyRate
* AuditLog

---

# 10. Expected Import Report

Example:

```
Import Summary
--------------
Rows Processed: 142
Expenses Imported: 131
Settlements Created: 3
Duplicate Entries: 4
Duplicate Entries Pending Approval: 2
USD Expenses Converted: 7
Negative Amounts Flagged: 1
Invalid Rows Skipped: 2
Unknown Members Created: 1
Manual Review Required: 3
Import Status: Completed with Warnings
```

---

# 11. Product Design Principles

* Never silently discard data.
* Never silently modify user data.
* Every anomaly must be detectable and explainable.
* Historical data should remain auditable.
* Users should be able to trace every balance back to the underlying expenses.
* The application should prioritize correctness and transparency over aggressive automation.

---

# 12. Advanced Product Features

## Expense Categories & Analytics
* Categorize expenses into configurable categories.
* Visualize spending trends and category-wise breakdowns.
* Track member-wise contributions over time.

## Export & Reporting
* Export balances, settlements, expense history, and import reports.
* Support CSV and PDF formats.

## Role-Based Permissions
* Admin and Member roles with separate privileges.
* Admin-controlled import approval and conflict resolution workflows.

## Import Center
The application should provide a dedicated Import Center where users can:
* Upload new CSV files.
* Review previous import sessions.
* View pending conflict resolutions.
* Download historical import reports.
* Track failed or partially completed imports.

## AI-Assisted Duplicate Detection
* Use similarity-based algorithms to suggest duplicate expenses.
* Never automatically delete or merge records without user approval.

## Recurring Expenses
Support automatically generated recurring expenses for:
* Rent.
* Electricity bills.
* Internet subscriptions.
* Other periodic payments.

Users should be able to configure frequency, start/end dates, and participant lists.
