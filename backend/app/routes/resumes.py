import json
import uuid
from pathlib import Path
from fastapi.responses import FileResponse

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_role
from app.database.session import get_db
from app.models.entities import Achievement, Application, Certification, CompanyProfile, Internship, Project, Resume, Skill, StudentProfile, StudentSkill, User, WorkExperience
from app.schemas import ResumeReviewInput
from app.resume_parser.parser import parse_resume

router = APIRouter(prefix="/api/resumes", tags=["resumes"])
ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


@router.post("/upload", status_code=201)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Upload a PDF or DOCX file")
    content = await file.read(settings.max_resume_size_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_resume_size_mb * 1024 * 1024:
        raise HTTPException(413, f"Resume exceeds {settings.max_resume_size_mb} MB")
    try:
        text, parsed = parse_resume(file.filename or "resume", content)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    directory = Path(settings.upload_dir) / str(student.id)
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.{(file.filename or 'resume').rsplit('.', 1)[-1].lower()}"
    path = directory / safe_name
    path.write_bytes(content)
    resume = Resume(student_id=student.id, filename=file.filename or safe_name, storage_path=str(path), extracted_text=text, parsed_data=json.dumps(parsed))
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return {"id": resume.id, "filename": resume.filename, "parsed": parsed, "message": "Review these extracted fields before applying them to your profile."}


@router.get("")
def list_resumes(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    return [{"id": resume.id, "filename": resume.filename, "created_at": resume.created_at} for resume in db.query(Resume).filter_by(student_id=student.id).order_by(Resume.created_at.desc()).all()]


@router.get("/{resume_id}")
def get_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    resume = db.query(Resume).filter_by(id=resume_id, student_id=student.id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")
    return {"id": resume.id, "filename": resume.filename, "parsed": json.loads(resume.parsed_data), "created_at": resume.created_at}


@router.post("/{resume_id}/confirm")
def confirm_parsed_resume(resume_id: int, payload: ResumeReviewInput, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    resume = db.query(Resume).filter_by(id=resume_id, student_id=student.id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")
    # Apply only explicitly reviewed, non-empty fields; omitted or blank values never erase existing data.
    for field, value in payload.profile.model_dump(exclude_unset=True, exclude_none=True).items():
        if value != "":
            setattr(student, field, value)
    added = {"skills": 0, "projects": 0, "certifications": 0, "work_experiences": 0}
    for item in payload.skills:
        name = item.name.strip()
        if not name:
            continue
        skill = db.query(Skill).filter(Skill.name.ilike(name)).first()
        if not skill:
            skill = Skill(name=name, category=item.category)
            db.add(skill)
            db.flush()
        exists = db.query(StudentSkill).filter_by(student_id=student.id, skill_id=skill.id).first()
        if not exists:
            db.add(StudentSkill(student_id=student.id, skill_id=skill.id, proficiency=item.proficiency))
            added["skills"] += 1
    for item in payload.projects:
        name = item.name.strip()
        if not name or db.query(Project).filter(Project.student_id == student.id, Project.name.ilike(name)).first():
            continue
        db.add(Project(student_id=student.id, name=name, description=item.description or None,
                       technologies=", ".join(dict.fromkeys(value.strip() for value in item.technologies if value.strip())), url=item.url or None))
        added["projects"] += 1
    for item in payload.certifications:
        title = item.title.strip()
        if not title or db.query(Certification).filter(Certification.student_id == student.id, Certification.title.ilike(title)).first():
            continue
        db.add(Certification(student_id=student.id, title=title, issuer=item.issuer or None, issue_date=item.issue_date, credential_url=item.credential_url or None))
        added["certifications"] += 1
    for item in payload.work_experiences:
        title, company = item.title.strip(), item.company.strip()
        if not title or not company or db.query(WorkExperience).filter(WorkExperience.student_id == student.id,
                WorkExperience.title.ilike(title), WorkExperience.company.ilike(company)).first():
            continue
        db.add(WorkExperience(student_id=student.id, title=title, company=company, description=item.description or None,
                              start_date=item.start_date, end_date=item.end_date))
        added["work_experiences"] += 1
    db.commit()
    return {"message": "Reviewed resume fields applied without replacing existing records", "added": added}


@router.get("/company/applications/{application_id}/latest")
def company_view_resume(application_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("company"))):
    company = db.query(CompanyProfile).filter_by(user_id=user.id).first()
    application = db.query(Application).join(Internship).filter(Application.id == application_id, Internship.company_id == company.id).first()
    if not application:
        raise HTTPException(404, "Application not found")
    resume = db.query(Resume).filter_by(student_id=application.student_id).order_by(Resume.created_at.desc()).first()
    if not resume or not Path(resume.storage_path).is_file():
        raise HTTPException(404, "No resume is available")
    return FileResponse(resume.storage_path, filename=resume.filename, content_disposition_type="attachment")
