# Decision Log

This document records the major architectural and design decisions made during the development of the Shared Expenses application.

---

### Decision 1: Tech Stack Selection (FastAPI + React/Vite)
**Options Considered:**
1. Next.js Full-Stack (Server Actions + React)
2. Django + Vanilla JS Templates
3. **FastAPI (Python) + Vite/React (Chosen)**

**Why we chose what we chose:**
We needed an extremely fast and type-safe backend to handle complex math operations (like debt simplification algorithms and CSV parsing). Python excels at data manipulation, and FastAPI provides automatic Swagger documentation and Pydantic validation out of the box, which made building the API incredibly fast. We paired this with React/Vite to ensure the user interface was modern, dynamic, and snappy without reloading the page.

### Decision 2: Database Engine (PostgreSQL vs SQLite)
**Options Considered:**
1. SQLite
2. **PostgreSQL via Neon (Chosen)**

**Why we chose what we chose:**
During early development, we used SQLite because it stores data in a simple local file, making it easy to test without internet. However, when we prepared for cloud deployment on Render, we realized Render's free tier uses ephemeral file systems (files are deleted every time the server restarts). If we kept SQLite, our database would be wiped daily! We switched to PostgreSQL hosted on Neon.tech, which provides a serverless, persistent database in the cloud, ensuring our users' financial data is never lost.

### Decision 3: Relational Structure for Expense Splitting
**Options Considered:**
1. Store an array of user IDs directly in the `Expenses` table (e.g., `split_among: ["user_1", "user_2"]`).
2. **Create a separate junction table `ExpenseParticipants` (Chosen)**

**Why we chose what we chose:**
Storing an array of IDs in a single column is easier to program initially. However, it completely breaks down if you want to support *uneven* splits (e.g., Alice pays 70%, Bob pays 30%). By creating a dedicated `ExpenseParticipants` table, each row links a user to an expense with an exact `amount_owed` column. This future-proofs the application for complex splitting logic without needing to completely rewrite the database schema.

### Decision 4: Handling CSV Edge Cases (Strict vs Loose Import)
**Options Considered:**
1. Loose Import: Accept every row, guess missing data, and let the user fix it later.
2. **Strict Import: Reject malformed rows and generate an error report (Chosen)**

**Why we chose what we chose:**
When dealing with financial data, making assumptions is dangerous. If we guess the wrong currency or attribute a debt to the wrong user because of a typo, it causes massive confusion for the group. We decided to be strict: if a row violates our data integrity rules (e.g., negative amounts, missing descriptions), we skip the row entirely and output a clear Import Report telling the user exactly which line failed and why. This maintains absolute trust in the application's math.
