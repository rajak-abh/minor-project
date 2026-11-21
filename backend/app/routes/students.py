import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import require_role
from app.database.session import get_db
from app.core.config import settings
from app.core.security import verify_password
from app.models.entities import Achievement, Application, AssessmentResult, Certification, MockInterview, Notification, PasswordResetToken, Project, Resume, Skill, StudentProfile, StudentSkill, User, UserPreference, WorkExperience
from app.schemas import AchievementInput, CertificationInput, DeleteAccountInput, PreferencesUpdate, ProfileUpdate, ProjectInput, SkillInput, WorkExperienceInput

router = APIRouter(prefix="/api/students/me", tags=["students"])


def get_profile(db: Session, user: User) -> StudentProfile:
    profile = db.query(StudentProfile).options(joinedload(StudentProfile.skills).joinedload(StudentSkill.skill)).filter_by(user_id=user.id).first()
    if profile is None:
        raise HTTPException(404, "Student profile not found")
    return profile


@router.get("")
def read_profile(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    return {"id": profile.id, "email": user.email, "role": user.role,
            "profile": {key: getattr(profile, key) for key in ("full_name", "phone", "date_of_birth", "location", "profile_picture_url", "university", "college", "degree", "branch", "current_semester", "cgpa", "graduation_year", "github_url", "linkedin_url", "portfolio_url")},
            "skills": [{"id": link.id, "skill_id": link.skill_id, "name": link.skill.name, "category": link.skill.category, "proficiency": link.proficiency} for link in profile.skills],
            "projects": [{"id": item.id, "name": item.name, "description": item.description, "technologies": item.technologies.split(", ") if item.technologies else [], "url": item.url} for item in profile.projects],
            "certifications": [{"id": item.id, "title": item.title, "issuer": item.issuer, "issue_date": item.issue_date, "credential_url": item.credential_url} for item in profile.certifications],
            "work_experiences": [{"id": item.id, "company": item.company, "title": item.title, "description": item.description, "start_date": item.start_date, "end_date": item.end_date} for item in profile.work_experiences],
            "achievements": [{"id": item.id, "title": item.title, "description": item.description, "achieved_on": item.achieved_on} for item in profile.achievements]}


@router.put("")
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return {"message": "Profile updated", "profile": {key: getattr(profile, key) for key in payload.model_fields}}


@router.get("/skills")
def list_skills(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    return [{"id": link.id, "name": link.skill.name, "category": link.skill.category, "proficiency": link.proficiency} for link in profile.skills]


@router.post("/skills", status_code=201)
def add_skill(payload: SkillInput, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    skill = db.query(Skill).filter(Skill.name.ilike(payload.name)).first()
    if skill is None:
        skill = Skill(name=payload.name.strip(), category=payload.category)
        db.add(skill)
        db.flush()
    existing = db.query(StudentSkill).filter_by(student_id=profile.id, skill_id=skill.id).first()
    if existing:
        raise HTTPException(409, "Skill already exists on this profile")
    link = StudentSkill(student_id=profile.id, skill_id=skill.id, proficiency=payload.proficiency)
    db.add(link)
    db.commit()
    return {"id": link.id, "name": skill.name, "category": skill.category, "proficiency": link.proficiency}


@router.delete("/skills/{skill_link_id}", status_code=204)
def remove_skill(skill_link_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    link = db.query(StudentSkill).filter_by(id=skill_link_id, student_id=profile.id).first()
    if not link:
        raise HTTPException(404, "Skill not found")
    db.delete(link)
    db.commit()


@router.post("/projects", status_code=201)
def add_project(payload: ProjectInput, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    item = Project(student_id=profile.id, name=payload.name, description=payload.description, technologies=", ".join(payload.technologies), url=payload.url)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/projects")
def list_projects(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    return [{"id": item.id, "name": item.name, "description": item.description, "technologies": item.technologies.split(", ") if item.technologies else [], "url": item.url}
            for item in db.query(Project).filter_by(student_id=profile.id).order_by(Project.id.desc()).all()]


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    item = db.query(Project).filter_by(id=project_id, student_id=profile.id).first()
    if not item:
        raise HTTPException(404, "Project not found")
    db.delete(item)
    db.commit()


@router.post("/certifications", status_code=201)
def add_certification(payload: CertificationInput, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    item = Certification(student_id=profile.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/certifications")
def list_certifications(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    return db.query(Certification).filter_by(student_id=profile.id).order_by(Certification.id.desc()).all()


@router.delete("/certifications/{certification_id}", status_code=204)
def delete_certification(certification_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    item = db.query(Certification).filter_by(id=certification_id, student_id=profile.id).first()
    if not item:
        raise HTTPException(404, "Certification not found")
    db.delete(item)
    db.commit()


@router.get("/work-experiences")
def list_work_experiences(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    return db.query(WorkExperience).filter_by(student_id=profile.id).all()


@router.post("/work-experiences", status_code=201)
def add_work_experience(payload: WorkExperienceInput, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    item = WorkExperience(student_id=profile.id, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.delete("/work-experiences/{item_id}", status_code=204)
def delete_work_experience(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    item = db.query(WorkExperience).filter_by(id=item_id, student_id=profile.id).first()
    if not item: raise HTTPException(404, "Work experience not found")
    db.delete(item); db.commit()


@router.get("/achievements")
def list_achievements(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    return db.query(Achievement).filter_by(student_id=profile.id).all()


@router.post("/achievements", status_code=201)
def add_achievement(payload: AchievementInput, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    item = Achievement(student_id=profile.id, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.delete("/achievements/{item_id}", status_code=204)
def delete_achievement(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    item = db.query(Achievement).filter_by(id=item_id, student_id=profile.id).first()
    if not item: raise HTTPException(404, "Achievement not found")
    db.delete(item); db.commit()


@router.post("/profile-picture", status_code=201)
async def upload_profile_picture(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    accepted = {"image/jpeg": ("jpg", b"\xff\xd8\xff"), "image/png": ("png", b"\x89PNG\r\n\x1a\n"), "image/webp": ("webp", b"RIFF")}
    if file.content_type not in accepted:
        raise HTTPException(415, "Upload a JPEG, PNG, or WebP image")
    content = await file.read(2 * 1024 * 1024 + 1)
    extension, signature = accepted[file.content_type]
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "Profile picture exceeds 2 MB")
    if not content.startswith(signature) or (extension == "webp" and content[8:12] != b"WEBP"):
        raise HTTPException(415, "Image content does not match its declared type")
    profile = get_profile(db, user)
    directory = Path(settings.upload_dir) / str(profile.id)
    directory.mkdir(parents=True, exist_ok=True)
    old_path = Path(settings.upload_dir) / str(profile.id) / profile.profile_picture_url.rsplit("/", 1)[-1] if profile.profile_picture_url else None
    filename = f"avatar-{uuid.uuid4().hex}.{extension}"
    (directory / filename).write_bytes(content)
    profile.profile_picture_url = f"/students/me/profile-picture/{filename}"
    db.commit()
    if old_path and old_path.is_file(): old_path.unlink()
    return {"profile_picture_url": profile.profile_picture_url}


@router.get("/profile-picture/{filename}")
def get_profile_picture(filename: str, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = get_profile(db, user)
    if profile.profile_picture_url != f"/students/me/profile-picture/{filename}":
        raise HTTPException(404, "Profile picture not found")
    path = Path(settings.upload_dir) / str(profile.id) / filename
    if not path.is_file(): raise HTTPException(404, "Profile picture not found")
    media_type = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(path.suffix.lstrip("."))
    return FileResponse(path, media_type=media_type)


@router.delete("", status_code=204)
def delete_account(payload: DeleteAccountInput, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(400, "Password confirmation failed")
    profile = get_profile(db, user)
    resume_directory = Path(settings.upload_dir) / str(profile.id)
    db.query(Application).filter_by(student_id=profile.id).delete(synchronize_session=False)
    db.query(AssessmentResult).filter_by(student_id=profile.id).delete(synchronize_session=False)
    db.query(MockInterview).filter_by(student_id=profile.id).delete(synchronize_session=False)
    db.query(Resume).filter_by(student_id=profile.id).delete(synchronize_session=False)
    db.query(Notification).filter_by(user_id=user.id).delete(synchronize_session=False)
    db.query(PasswordResetToken).filter_by(user_id=user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    if resume_directory.exists():
        for path in resume_directory.iterdir():
            if path.is_file(): path.unlink()
        resume_directory.rmdir()


@router.get("/preferences")
def get_preferences(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    preferences = db.query(UserPreference).filter_by(user_id=user.id).first()
    if preferences is None:
        return {"notifications_enabled": True, "weekly_report": True, "compact_mode": False}
    return {"notifications_enabled": preferences.notifications_enabled, "weekly_report": preferences.weekly_report, "compact_mode": preferences.compact_mode}


@router.put("/preferences")
def update_preferences(payload: PreferencesUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    preferences = db.query(UserPreference).filter_by(user_id=user.id).first()
    if preferences is None:
        preferences = UserPreference(user_id=user.id)
        db.add(preferences)
    for field, value in payload.model_dump().items(): setattr(preferences, field, value)
    db.commit()
    return payload.model_dump()
