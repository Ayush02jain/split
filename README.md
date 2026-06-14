# Shared Expenses Application

Welcome to the Shared Expenses App! This is a full-stack web application designed to help groups of friends, roommates, or colleagues easily track shared expenses and calculate exactly who owes who.

## Features
- **Group Management:** Create groups and add members.
- **Expense Tracking:** Add expenses and split them equally among group members.
- **CSV Import:** Bulk-import expenses from a CSV file with automatic error detection (anomalies).
- **Debt Calculation:** Automatically calculates total balances and simplifies debts between members.

## Technology Stack
- **Frontend:** React + Vite (Fast, modern user interface)
- **Backend:** FastAPI (Python) for extremely fast and robust API endpoints
- **Database:** PostgreSQL (Neon Serverless Postgres)
- **Deployment:** Vercel (Frontend) and Render (Backend)

---

## Local Setup Instructions

If you want to run this application on your own computer, follow these simple steps:

### 1. Database Setup
We use PostgreSQL. The easiest way is to create a free database on [Neon.tech](https://neon.tech/):
1. Create a project and copy the connection string (it looks like `postgresql://user:password@server...`).
2. Create a `.env` file in the `backend/` folder.
3. Paste your connection string inside like this:
   ```env
   DATABASE_URL=postgresql://your_neon_string_here
   SECRET_KEY=my-super-secret-key-123
   ```

### 2. Backend Setup
The backend runs on Python.
1. Open a terminal and navigate to the `backend/` folder.
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the backend server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. The backend will now be running at `http://localhost:8000`.

### 3. Frontend Setup
The frontend runs on Node.js and React.
1. Open a second terminal and navigate to the `frontend/` folder.
2. Install the required Node packages:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. The frontend will open in your browser at `http://localhost:5175`.

---

## AI Tools Used
During the development of this project, **Google Gemini (Antigravity)** was used as an AI pair programmer. 
The AI assisted in generating the base FastAPI architecture, writing the React components, configuring the database schema, and troubleshooting complex deployment errors on Vercel and Render. 

*For a detailed log of AI prompts, mistakes, and corrections, please see the `AI_USAGE.md` file.*
