# CSV Import Report

**Date of Import:** June 15, 2026
**File Processed:** `expenses_export.csv`
**Total Rows Scanned:** 15

---

## Summary
- ✅ **Successfully Imported:** 12 expenses
- ⚠️ **Warnings (Imported with modifications):** 1 expense
- ❌ **Fatal Errors (Row skipped completely):** 2 expenses

---

## Detailed Anomaly Log

### ❌ Fatal Errors
The following rows violated strict data integrity rules and were **NOT** imported into the database. You must fix these in the CSV and re-upload.

1. **Row 5 Skipped:** 
   - *Issue:* `Missing required field 'Description'.`
   - *Action Taken:* Skipped row. Every expense must have a description to be tracked accurately.

2. **Row 11 Skipped:**
   - *Issue:* `User 'Charlie' not found in group.`
   - *Action Taken:* Skipped row. The user listed in the "Paid By" column does not exist in this group. Please invite Charlie to the group before importing his expenses.

### ⚠️ Warnings
The following rows had minor anomalies. The system automatically corrected the data and imported the expense.

1. **Row 8 Imported with Warning:**
   - *Issue:* `Converted unrecognized currency 'EUR' to default base currency.`
   - *Action Taken:* The system currently operates on a single base currency. The numerical amount `45.00` was imported, but please be aware it is now being treated as the default currency.

### ✅ Successful Imports
*Rows 1-4, 6-7, 9-10, 12-15 were cleanly imported without any data anomalies.*
