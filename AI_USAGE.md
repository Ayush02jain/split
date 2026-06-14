# AI Usage Log

This document details how Artificial Intelligence was utilized to build the Shared Expenses application.

**AI Tool Used:** Google Gemini (Antigravity IDE Assistant)

## Key Prompts Used
- *"I need a React component for a dashboard that displays three StatCards: Total group debt, Total expenses, and Your balance. Use clean CSS without Tailwind."*
- *"Help me write a Python script using pandas to parse a messy CSV file and find rows where the amount is negative or missing."*
- *"How do I configure FastAPI to connect to a Neon serverless PostgreSQL database using SQLAlchemy?"*
- *"I'm getting an `npm error ERESOLVE could not resolve` when deploying my Vite app to Vercel. How do I fix this?"*

---

## AI Mistakes and Corrections

While the AI was incredibly helpful for writing boilerplate code and explaining concepts, there were several instances where it made mistakes that I had to catch and correct.

### Case 1: The Pydantic Email Validator Crash
- **What the AI did wrong:** When generating the `requirements.txt` for the Python backend, the AI wrote `pydantic[email-validator]==2.9.2`. 
- **How I caught it:** When deploying the backend to Render, the build process succeeded but the app immediately crashed on startup. I checked the Render Runtime Logs and saw the error: `ImportError: email-validator is not installed, run pip install pydantic[email]`.
- **What I changed:** I realized the AI used the wrong package extra syntax. I manually opened `requirements.txt`, changed `pydantic[email-validator]` to the correct syntax `pydantic[email]`, added `email-validator==2.2.0` explicitly, and pushed the fix to GitHub.

### Case 2: Vercel Peer Dependency Conflict
- **What the AI did wrong:** The AI instructed me to deploy the React frontend to Vercel using the default settings. It assumed the standard `npm install` command would work perfectly for the Vite template it generated.
- **How I caught it:** The Vercel deployment failed with a massive `ERESOLVE` error regarding `@eslint/js` and `eslint@8.57.0`.
- **What I changed:** I researched the error and realized that modern npm versions are extremely strict about peer dependencies, which causes issues with slightly mismatched React templates. I fixed this by going into the Vercel Build & Development settings and manually overriding the install command to `npm install --legacy-peer-deps` so it would ignore the minor conflict.

### Case 3: Local SQLite vs Cloud PostgreSQL Configuration
- **What the AI did wrong:** Early in the project, the AI configured the SQLAlchemy database connection to use a local SQLite file (`sqlite:///./sql_app.db`). Later, when we moved to the cloud, the AI told me to put my Neon Postgres URL into the environment variables, but it didn't update the `config.py` file to actually read from the `.env` file securely.
- **How I caught it:** I realized my data wasn't showing up on the deployed version. I looked at the code and saw the connection string was still hardcoded to SQLite in the main codebase instead of dynamically reading the `DATABASE_URL`.
- **What I changed:** I rewrote `config.py` to use `pydantic-settings` to securely load `DATABASE_URL` from the `.env` file, ensuring that the local environment could still test things securely while the production environment connected to Neon.
