import pytest
from io import BytesIO
import pymupdf
import pytesseract
from PIL import Image
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import app
from app.ml.recommender import load_vectorizer, recommend, train_recommender
from app.resume_parser.parser import parse_resume
from app.resume_parser import parser as resume_parser
from app.core.config import settings
from app.middleware.rate_limit import SensitiveRouteRateLimit
from starlette.requests import Request
from starlette.responses import PlainTextResponse


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_recommender_returns_deterministic_skill_explanation():
    internships = [{"id": 1, "title": "Python Intern", "description": "Use Python and SQL for data projects", "skills": ["Python", "SQL", "TensorFlow"], "min_cgpa": 7.0}]
    first = recommend(["Python", "SQL"], "Computer science Python data", 8.0, internships)
    second = recommend(["Python", "SQL"], "Computer science Python data", 8.0, internships)
    assert first == second
    assert first[0]["matching_skills"] == ["Python", "SQL"]
    assert first[0]["missing_skills"] == ["TensorFlow"]
    assert 0 <= first[0]["match_percentage"] <= 100


def test_recommender_handles_empty_catalogue_and_ineligible_student():
    assert recommend([], "", None, []) == []
    result = recommend([], "", 5.0, [{"id": 1, "title": "Role", "description": "", "skills": ["Go"], "min_cgpa": 7.0}])
    assert result[0]["match_percentage"] == 0
    assert result[0]["eligible"] is False


def test_joblib_recommender_can_train_on_small_catalogue(tmp_path):
    model_path = tmp_path / "tfidf.joblib"
    catalogue = [{"id": 1, "title": "Python Data Intern", "description": "Analyze datasets with Python", "skills": ["Python"], "min_cgpa": None}]
    outcome = train_recommender(catalogue, model_path)
    assert outcome["trained"] is True
    assert model_path.is_file()
    matches = recommend(["Python"], "Python data analysis", 8.0, catalogue, load_vectorizer(model_path))
    assert matches[0]["match_percentage"] > 0


def test_resume_rejects_unsupported_file():
    with pytest.raises(ValueError, match="Only PDF and DOCX"):
        parse_resume("resume.txt", b"text")


def test_resume_rejects_invalid_pdf():
    with pytest.raises(ValueError, match="corrupted"):
        parse_resume("resume.pdf", b"not a pdf")


def test_resume_parses_docx_contact_and_skills():
    document = Document()
    document.add_paragraph("Jordan Student")
    document.add_paragraph("jordan@example.edu")
    document.add_paragraph("+1 555 123 4567")
    document.add_paragraph("Skills: Python, React, SQL")
    from io import BytesIO
    buffer = BytesIO()
    document.save(buffer)
    _, parsed = parse_resume("resume.docx", buffer.getvalue())
    assert parsed["name"] == "Jordan Student"
    assert parsed["email"] == "jordan@example.edu"
    assert "Python" in parsed["skills"]


def test_resume_parses_education_and_structured_sections():
    document = Document()
    for line in ["Morgan Lee", "Education:", "University: North Campus University", "College: School of Engineering", "Degree: B.Tech Computer Science", "Branch: Computer Science", "CGPA: 8.4", "Graduation Year: 2027", "Projects:", "Campus Planner", "Experience:", "Software Intern at Acme Labs", "Certifications:", "Cloud Foundations - Acme Academy"]:
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    _, parsed = parse_resume("resume.docx", buffer.getvalue())
    assert parsed["education_details"]["university"] == "North Campus University"
    assert parsed["education_details"]["cgpa"] == 8.4
    assert parsed["projects"][0]["name"] == "Campus Planner"
    assert parsed["experience"][0]["company"] == "Acme Labs"
    assert parsed["certifications"][0]["issuer"] == "Acme Academy"


def _image_only_pdf():
    image = Image.new("RGB", (80, 40), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    pdf = pymupdf.open()
    page = pdf.new_page(width=200, height=100)
    page.insert_image(page.rect, stream=buffer.getvalue())
    return pdf.tobytes()


def test_scanned_pdf_uses_ocr_when_tesseract_is_available(monkeypatch):
    monkeypatch.setattr(settings, "tesseract_cmd", None)
    monkeypatch.setattr(resume_parser.shutil, "which", lambda _: "tesseract")
    monkeypatch.setattr(pytesseract, "image_to_string", lambda *_args, **_kwargs: "Taylor Student\ntaylor@example.edu\nPython SQL")
    _, parsed = parse_resume("scanned.pdf", _image_only_pdf())
    assert parsed["email"] == "taylor@example.edu"
    assert "Python" in parsed["skills"]


def test_scanned_pdf_returns_actionable_error_without_tesseract(monkeypatch):
    monkeypatch.setattr(settings, "tesseract_cmd", None)
    monkeypatch.setattr(resume_parser.shutil, "which", lambda _: None)
    with pytest.raises(ValueError, match="Install Tesseract OCR"):
        parse_resume("scanned.pdf", _image_only_pdf())


def test_shared_rate_limit_uses_common_redis_counter():
    class FakeRedis:
        def __init__(self): self.counts = {}
        async def eval(self, _script, _keys, key, _window):
            self.counts[key] = self.counts.get(key, 0) + 1
            return [self.counts[key], 60]

    shared = FakeRedis()
    first = SensitiveRouteRateLimit(lambda *_: None, limit=2, redis_url="redis://test")
    second = SensitiveRouteRateLimit(lambda *_: None, limit=2, redis_url="redis://test")
    first.redis = shared
    second.redis = shared
    scope = {"type": "http", "method": "POST", "path": "/api/auth/login", "headers": [], "query_string": b"", "server": ("test", 80), "client": ("192.0.2.2", 1000), "scheme": "http", "http_version": "1.1"}
    async def call_next(_request): return PlainTextResponse("ok")

    async def exercise():
        assert (await first.dispatch(Request(scope), call_next)).status_code == 200
        assert (await second.dispatch(Request(scope), call_next)).status_code == 200
        blocked = await first.dispatch(Request(scope), call_next)
        assert blocked.status_code == 429
        assert blocked.headers["Retry-After"] == "60"

    import anyio
    anyio.run(exercise)


def test_registration_login_and_role_protected_profile(client):
    registered = client.post("/api/auth/register", json={"email": "learner@example.com", "password": "secure-passphrase-123", "full_name": "Learner"})
    assert registered.status_code == 201
    token = registered.json()["access_token"]
    profile = client.get("/api/students/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["profile"]["full_name"] == "Learner"
    assert client.post("/api/students/me/projects", json={"name": "Portfolio", "technologies": ["React"]}, headers={"Authorization": f"Bearer {token}"}).status_code == 201
    assert client.post("/api/students/me/certifications", json={"title": "Python Basics"}, headers={"Authorization": f"Bearer {token}"}).status_code == 201
    refreshed = client.get("/api/students/me", headers={"Authorization": f"Bearer {token}"})
    assert refreshed.json()["projects"][0]["technologies"] == ["React"]
    assert refreshed.json()["certifications"][0]["title"] == "Python Basics"
    assert client.post("/api/auth/login", json={"email": "learner@example.com", "password": "wrong-password"}).status_code == 401


def test_student_cannot_create_company_internship(client):
    response = client.post("/api/auth/register", json={"email": "student@example.com", "password": "secure-passphrase-123"})
    token = response.json()["access_token"]
    denied = client.post("/api/internships", json={"title": "Role", "description": "Role text"}, headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 403


def test_duplicate_internship_application_is_rejected(client):
    student_response = client.post("/api/auth/register", json={"email": "student@example.com", "password": "secure-passphrase-123"})
    company_response = client.post("/api/auth/register", json={"email": "company@example.com", "password": "secure-passphrase-123", "role": "company", "company_name": "Demo Co"})
    company_token = company_response.json()["access_token"]
    created = client.post("/api/internships", json={"title": "Backend Intern", "description": "Build APIs", "skills": ["Python"]}, headers={"Authorization": f"Bearer {company_token}"})
    assert created.status_code == 201
    student_token = student_response.json()["access_token"]
    payload = {"internship_id": created.json()["id"]}
    assert client.post("/api/applications", json=payload, headers={"Authorization": f"Bearer {student_token}"}).status_code == 201
    assert client.post("/api/applications", json=payload, headers={"Authorization": f"Bearer {student_token}"}).status_code == 409


def test_company_can_update_only_its_own_applications(client):
    student_token = client.post("/api/auth/register", json={"email": "applicant@example.com", "password": "valid-account-password"}).json()["access_token"]
    owner_token = client.post("/api/auth/register", json={"email": "owner@example.com", "password": "valid-account-password", "role": "company", "company_name": "Owner Co"}).json()["access_token"]
    other_token = client.post("/api/auth/register", json={"email": "other@example.com", "password": "valid-account-password", "role": "company", "company_name": "Other Co"}).json()["access_token"]
    job = client.post("/api/internships", json={"title": "API Intern", "description": "Build APIs"}, headers={"Authorization": f"Bearer {owner_token}"}).json()
    application = client.post("/api/applications", json={"internship_id": job["id"]}, headers={"Authorization": f"Bearer {student_token}"}).json()
    path = f"/api/applications/{application['id']}/status"
    assert client.put(path, json={"status": "Shortlisted"}, headers={"Authorization": f"Bearer {owner_token}"}).status_code == 200
    assert client.put(path, json={"status": "Rejected"}, headers={"Authorization": f"Bearer {other_token}"}).status_code == 404


def test_password_reset_and_logout_revoke_refresh_token(client):
    registered = client.post("/api/auth/register", json={"email": "reset@example.com", "password": "initial-password-123"}).json()
    requested = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"}).json()
    assert requested.get("development_reset_token")
    reset = client.post("/api/auth/reset-password", json={"token": requested["development_reset_token"], "password": "replacement-password-123"})
    assert reset.status_code == 200
    assert client.post("/api/auth/login", json={"email": "reset@example.com", "password": "initial-password-123"}).status_code == 401
    login = client.post("/api/auth/login", json={"email": "reset@example.com", "password": "replacement-password-123"}).json()
    access = login["access_token"]
    logout = client.post("/api/auth/logout", json={"refresh_token": login["refresh_token"]}, headers={"Authorization": f"Bearer {access}"})
    assert logout.status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401


def test_preferences_and_account_deletion_are_account_scoped(client):
    registered = client.post("/api/auth/register", json={"email": "prefs@example.com", "password": "valid-account-password"}).json()
    auth = {"Authorization": f"Bearer {registered['access_token']}"}
    saved = client.put("/api/students/me/preferences", json={"notifications_enabled": False, "weekly_report": True, "compact_mode": True}, headers=auth)
    assert saved.status_code == 200
    assert client.get("/api/students/me/preferences", headers=auth).json()["compact_mode"] is True
    assert client.request("DELETE", "/api/students/me", json={"password": "wrong-password"}, headers=auth).status_code == 400
    assert client.request("DELETE", "/api/students/me", json={"password": "valid-account-password"}, headers=auth).status_code == 204
    assert client.get("/api/auth/me", headers=auth).status_code == 401


def test_resume_confirmation_saves_all_reviewed_sections_without_overwriting(client, tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    token = client.post("/api/auth/register", json={"email": "resume-review@example.com", "password": "valid-account-password", "full_name": "Original Name"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    client.post("/api/students/me/skills", json={"name": "Python", "proficiency": 90}, headers=auth)
    client.post("/api/students/me/projects", json={"name": "Existing Project"}, headers=auth)
    document = Document()
    document.add_paragraph("Casey Student")
    document.add_paragraph("casey@example.edu")
    buffer = BytesIO(); document.save(buffer)
    uploaded = client.post("/api/resumes/upload", headers=auth, files={"file": ("resume.docx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert uploaded.status_code == 201
    resume_id = uploaded.json()["id"]
    review = client.post(f"/api/resumes/{resume_id}/confirm", headers=auth, json={
        "profile": {"full_name": "Casey Student", "degree": "B.Tech", "cgpa": 8.2},
        "skills": [{"name": "Python", "proficiency": 50}, {"name": "React", "proficiency": 70}],
        "projects": [{"name": "Reviewed Project", "technologies": ["React"]}],
        "certifications": [{"title": "Cloud Basics", "issuer": "Example Org"}],
        "work_experiences": [{"title": "Developer Intern", "company": "Example Co", "description": "Built APIs"}],
    })
    assert review.status_code == 200
    assert review.json()["added"] == {"skills": 1, "projects": 1, "certifications": 1, "work_experiences": 1}
    profile = client.get("/api/students/me", headers=auth).json()
    assert profile["profile"]["full_name"] == "Casey Student"
    assert profile["profile"]["branch"] is None
    assert {item["name"] for item in profile["projects"]} == {"Existing Project", "Reviewed Project"}
    skills = client.get("/api/students/me/skills", headers=auth).json()
    assert next(item for item in skills if item["name"] == "Python")["proficiency"] == 90
    assert client.get("/api/students/me/certifications", headers=auth).json()[0]["title"] == "Cloud Basics"
    assert client.get("/api/students/me/work-experiences", headers=auth).json()[0]["company"] == "Example Co"
