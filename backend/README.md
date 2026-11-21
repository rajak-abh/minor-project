# Student Skills and Internship Tracker API

FastAPI + SQLAlchemy API for the existing React application. API docs are served at `/docs` after startup.

## Local setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a unique `JWT_SECRET_KEY` in `.env` before using non-demo accounts. SQLite is configured for local development; set `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/skilltrack` for PostgreSQL. Configure SMTP settings to send password reset tokens. Without SMTP, the API exposes a reset token only in development mode. Create an administrator from a trusted shell using `python create_admin.py admin@example.edu` after applying migrations.

```powershell
python -m alembic upgrade head
$env:APP_ENV = 'development'
python seed.py
python -m uvicorn app.main:app --reload
```

Frontend: from `frontend/my-application`, run `npm install` and `npm run dev` in a separate terminal. Set `VITE_API_URL` to the API base URL (default `http://127.0.0.1:8000/api`). Keep the API process running in its terminal while using signup/login.

## Container deployment

The repository `docker-compose.yml` runs PostgreSQL, Redis, the API, and the frontend with persistent database, resume, and recommender-artifact volumes. Provide `POSTGRES_PASSWORD`, a long random `JWT_SECRET_KEY`, and the public `CORS_ORIGINS` in the deployment environment, then run `docker compose up --build -d`. The API applies Alembic migrations at container startup and requires Redis in production for shared credential-endpoint throttling. The API image installs Tesseract OCR with English language data. Set `VITE_API_URL` to the externally reachable API URL before building the frontend image; Vite embeds this value in the static bundle. Terminate HTTPS at a reverse proxy/load balancer and restrict public database/Redis access. Create an admin account using a one-off backend container shell after startup.

## Implemented API

- Student/company registration and login with Argon2 password hashes, signed access/refresh JWTs, and revocation on logout; role checks on protected routes. Admin creation is a trusted CLI operation and admin management endpoints are role-protected.
- Student profile, normalized skill links, projects, certifications, work history, achievements, account preferences and account deletion; company-owned internship CRUD; student applications and status updates with duplicate prevention and ownership checks.
- Resume PDF/DOCX text extraction, parsed fields for user review, upload size/type checks, and per-student file storage; company resume download verifies the application belongs to that company.
- Deterministic TF-IDF/cosine and exact-skill internship recommendations, eligibility filtering, a Joblib-saved catalogue vectorizer with an admin retrain endpoint, assessments with answer evaluation/history, question-bank interview practice/history, and student/company analytics.
- Alembic initial schema migration, development-only seed data, Swagger docs.

Password reset tokens expire after 30 minutes and can be delivered by configured SMTP; local development returns the token in the response. Logout revokes the access and refresh tokens stored in the database. Text-based PDF and DOCX files are supported. Scanned PDF pages are OCRed with Tesseract when available; install the Tesseract binary locally, or use the provided API image which includes English Tesseract. Sensitive routes use Redis-backed limits across API workers when `RATE_LIMIT_REDIS_URL` is configured; production startup requires this setting. Uploaded resumes and profile images use a private local directory; use private object storage for multi-instance deployment. Set CORS origins, secrets, PostgreSQL, file storage, and TLS for deployment.

## Tests

```powershell
python -m pytest
```

The serialized placement-readiness classifier under `../minor project/Minor-Project/models` is separate from the internship recommender. It uses a developer-specific default path today; configure/update that pipeline before exposing it via an API. Recommendation matches are calculated from the current internship catalogue and student data, so the pipeline works with small catalogues without invented training labels.
