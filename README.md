# Student Skills and Internship Tracker

This repository contains the existing React/Vite student dashboard (`frontend/my-application`), an existing placement prediction research pipeline (`minor project/Minor-Project`), and the new FastAPI service (`backend`).

## Run locally

1. Follow [backend setup](backend/README.md) to create the environment, install dependencies, apply migrations, and run the API. Keep that terminal open. Check `http://127.0.0.1:8000/api/health` responds with `{"status":"ok",...}`.
2. In a second terminal, go to `frontend/my-application`, run `npm install`, copy `.env.example` to `.env`, and run `npm run dev`.
3. Open the exact URL printed by Vite (usually `http://localhost:5173`) and register. Student profile, skills, projects, certifications, applications, assessments, and interview history save through the API to the database. Each save now shows progress and success or an error.

The local SQLite database and uploaded files use paths anchored to `backend`, even if the API or migration command is started from another working directory. To confirm which DB is in use, inspect `DATABASE_URL` in `backend/.env`.

Seed accounts and postings are synthetic and restricted to `APP_ENV=development`. Change the JWT secret before using any real data. See [development progress](DEVELOPMENT_PROGRESS.md) for implemented scope and remaining work.
