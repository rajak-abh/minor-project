# Student Skills and Internship Tracker — Development Progress

## Existing project inspection

- Frontend: `frontend/my-application` is a React 19 + Vite app using React Router and hand-written CSS. There is no API client, backend configuration, authentication, or charting dependency.
- Routes: dashboard, profile, internships, projects, certifications, skills, mock interviews, performance, and settings. Navigation lives in `src/components/side2.jsx`.
- Current data: profile and dashboard identity/metrics are hardcoded; internship, project, skill, certification, and performance pages use local demo state/data. Settings alone persist preferences in browser local storage. Mock interviews have a fixed question bank and correctly label their review checklist as self-review, but do not persist history.
- Existing design: dark dashboard cards, fixed sidebar, and custom CSS in `src/index.css` and `src/App.css`. There are duplicate/overlapping layout rules and some mojibake in icon/text labels.
- ML project: `minor project/Minor-Project` contains a Python/scikit-learn placement-readiness pipeline, trained Joblib artifacts, processed/raw CSV data, reports, and a synthetic-data generation/training workflow. `src/predict.py` currently defaults to an absolute developer-specific Windows model path. Its placement classifier is distinct from the requested internship-content matching recommender and needs a separate, profile-based TF-IDF/cosine recommender.
- No `AGENTS.md` was found during inspection. Frontend `README.md` is still the Vite template. The ML README contains a stale merge-conflict marker near its end.

## Implementation plan

1. Establish a FastAPI backend with environment-driven configuration, SQLAlchemy relational models, Alembic migrations, password hashing/JWT, role and ownership checks, and API documentation.
2. Implement core student/company/admin auth, profile, skills, projects, certifications, resume, internships, applications, recommendations, analytics, assessments, and mock interview APIs.
3. Integrate PDF/DOCX text extraction with explicit parsing errors and review-before-save behavior; build deterministic TF-IDF/cosine plus skill/eligibility matching that also works with small datasets.
4. Connect the existing React routes using an Axios API/auth layer, protected routes, loading/error/empty states, and responsive styling while retaining the established UI.
5. Add seed/setup/deployment documentation and tests for critical API and ML behavior; validate installation/build/tests where the local environment permits.

## Status

- Completed: project inspection/plan; FastAPI/SQLAlchemy configuration; normalized core database entities; Alembic migrations; Argon2/JWT auth, refresh rotation/revocation, reset tokens/email support and student/company/admin role checks; Redis-shared sensitive-route limits with a local-development fallback; student profile/skill/project/certification/work/achievement APIs; profile image upload and account deletion; saved preferences; editable company profile and company internship CRUD; student browse/apply/status APIs; duplicate application prevention; PDF/DOCX extraction, OCR integration, editable review, and non-destructive confirmation for education/profile fields, skills, projects, experience, and certifications; company-authorized resume download; deterministic TF-IDF/skill recommender with Joblib vectorizer artifact and admin retraining; assessments and interview question-bank/history APIs; student/company analytics APIs; admin user/internship/activity APIs and shell-only admin bootstrap; development seed script; React role-gated auth with access-token refresh, profile/skills/projects/certifications/internships pages, resume review, dashboard recommendations and Recharts analytics, company profile/posting/applicant management and candidate filters, admin dashboard, assessment UI, saved mock-interview history, assessment performance charts; setup/API/container deployment documentation; unit and API tests.
- Verified: frontend build succeeds with route-level code splitting; frontend lint succeeds; npm audit reports zero vulnerabilities; SQLite migrations apply; PostgreSQL migration SQL generates successfully in Alembic offline mode; Compose YAML parses and contains PostgreSQL, Redis, API, and web services; 17 backend tests pass, including full resume confirmation, OCR adapter/fallback, shared rate-limit behavior, auth/reset/role/ownership/application flows, and saved TF-IDF training.
- In progress: live deployment verification.
- Pending: live deployment verification against PostgreSQL, Docker Compose, a Redis server, and the containerized Tesseract binary. This environment has no Docker, PostgreSQL client/server, Redis server, or Tesseract executable, so those integration checks cannot run here. Redis coordination and OCR extraction are covered by mocked unit tests, and OCR missing-binary handling is tested directly.

## Known environment dependencies

- PostgreSQL is the preferred production database; local development can use SQLite via a configured database URL.
- A production JWT secret, PostgreSQL connection, and outbound email provider are deployment configuration. Password reset will have a development-safe token flow if no email provider is configured.
- OCR for image-only/scanned resumes uses Tesseract; the provided API Docker image installs the English language pack. Local API environments must install Tesseract separately.
- LLM feedback is optional; without a configured API key, interview practice must remain question-bank/self-review based and clearly labeled.
