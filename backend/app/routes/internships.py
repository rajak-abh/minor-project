from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import current_user, require_role
from app.database.session import get_db
from app.ml.recommender import load_vectorizer, recommend, train_recommender
from app.models.entities import Application, CompanyProfile, Internship, InternshipSkill, Skill, StudentProfile, StudentSkill, User
from app.schemas import ApplicationInput, CompanyInput, InternshipInput, StatusUpdate

router = APIRouter(prefix="/api", tags=["internships and applications"])
STATUSES = {"Applied", "Under Review", "Shortlisted", "Interview Scheduled", "Selected", "Rejected"}


def as_dict(item: Internship):
    return {"id": item.id, "title": item.title, "description": item.description, "location": item.location,
            "stipend": item.stipend, "duration": item.duration, "min_cgpa": item.min_cgpa, "deadline": item.deadline,
            "company_id": item.company_id, "company_name": item.company.name,
            "skills": [link.skill.name for link in item.skills], "created_at": item.created_at}


def company_for(db: Session, user: User) -> CompanyProfile:
    company = db.query(CompanyProfile).filter_by(user_id=user.id).first()
    if not company:
        raise HTTPException(404, "Company profile not found")
    return company


@router.get("/company/me")
def get_company_profile(db: Session = Depends(get_db), user: User = Depends(require_role("company"))):
    company = company_for(db, user)
    return {"name": company.name, "website": company.website, "description": company.description, "location": company.location, "email": user.email}


@router.put("/company/me")
def update_company_profile(payload: CompanyInput, db: Session = Depends(get_db), user: User = Depends(require_role("company"))):
    company = company_for(db, user)
    for field, value in payload.model_dump().items():
        setattr(company, field, value)
    db.commit()
    return {"name": company.name, "website": company.website, "description": company.description, "location": company.location, "email": user.email}


def save_internship(db: Session, item: Internship, payload: InternshipInput):
    for field in ("title", "description", "location", "stipend", "duration", "min_cgpa", "deadline"):
        setattr(item, field, getattr(payload, field))
    db.flush()
    db.query(InternshipSkill).filter_by(internship_id=item.id).delete()
    for name in dict.fromkeys(skill.strip() for skill in payload.skills if skill.strip()):
        skill = db.query(Skill).filter(Skill.name.ilike(name)).first()
        if skill is None:
            skill = Skill(name=name)
            db.add(skill)
            db.flush()
        db.add(InternshipSkill(internship_id=item.id, skill_id=skill.id))


@router.get("/internships")
def browse_internships(q: str | None = None, location: str | None = None, skill: str | None = None,
                       min_stipend: float | None = Query(default=None, ge=0), db: Session = Depends(get_db)):
    query = db.query(Internship).filter(Internship.is_active.is_(True))
    if location:
        query = query.filter(Internship.location.ilike(f"%{location}%"))
    if min_stipend is not None:
        query = query.filter(Internship.stipend >= min_stipend)
    rows = query.order_by(Internship.created_at.desc()).all()
    result = [as_dict(row) for row in rows]
    if q:
        result = [item for item in result if q.casefold() in (item["title"] + " " + item["description"]).casefold()]
    if skill:
        result = [item for item in result if skill.casefold() in [x.casefold() for x in item["skills"]]]
    return result


@router.get("/company/internships")
def company_internships(db: Session = Depends(get_db), user: User = Depends(require_role("company"))):
    company = company_for(db, user)
    return [as_dict(item) for item in db.query(Internship).filter_by(company_id=company.id, is_active=True).order_by(Internship.created_at.desc()).all()]


@router.get("/internships/{internship_id}")
def get_internship(internship_id: int, db: Session = Depends(get_db)):
    item = db.get(Internship, internship_id)
    if not item or not item.is_active:
        raise HTTPException(404, "Internship not found")
    return as_dict(item)


@router.post("/internships", status_code=201)
def create_internship(payload: InternshipInput, db: Session = Depends(get_db), user: User = Depends(require_role("company"))):
    company = company_for(db, user)
    item = Internship(company_id=company.id, title=payload.title, description=payload.description)
    db.add(item)
    db.flush()
    save_internship(db, item, payload)
    db.commit()
    db.refresh(item)
    return as_dict(item)


@router.put("/internships/{internship_id}")
def update_internship(internship_id: int, payload: InternshipInput, db: Session = Depends(get_db), user: User = Depends(require_role("company"))):
    company = company_for(db, user)
    item = db.query(Internship).filter_by(id=internship_id, company_id=company.id).first()
    if not item:
        raise HTTPException(404, "Internship not found")
    save_internship(db, item, payload)
    db.commit()
    return as_dict(item)


@router.delete("/internships/{internship_id}", status_code=204)
def delete_internship(internship_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("company"))):
    company = company_for(db, user)
    item = db.query(Internship).filter_by(id=internship_id, company_id=company.id).first()
    if not item:
        raise HTTPException(404, "Internship not found")
    item.is_active = False
    db.commit()


@router.post("/applications", status_code=201)
def apply(payload: ApplicationInput, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    internship = db.get(Internship, payload.internship_id)
    if not student or not internship or not internship.is_active:
        raise HTTPException(404, "Student or active internship not found")
    if internship.deadline and internship.deadline < date.today():
        raise HTTPException(400, "Application deadline has passed")
    if db.query(Application).filter_by(student_id=student.id, internship_id=internship.id).first():
        raise HTTPException(409, "You have already applied to this internship")
    item = Application(student_id=student.id, internship_id=internship.id)
    db.add(item)
    db.commit()
    return {"id": item.id, "internship_id": item.internship_id, "status": item.status}


@router.get("/applications/my-applications")
def my_applications(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    return [{"id": row.id, "status": row.status, "created_at": row.created_at, "internship": as_dict(row.internship)} for row in db.query(Application).filter_by(student_id=student.id).all()]


@router.put("/applications/{application_id}/status")
def update_status(application_id: int, payload: StatusUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("company", "admin"))):
    if payload.status not in STATUSES:
        raise HTTPException(422, "Unsupported application status")
    query = db.query(Application).filter_by(id=application_id)
    if user.role == "company":
        company = company_for(db, user)
        query = query.join(Internship).filter(Internship.company_id == company.id)
    item = query.first()
    if not item:
        raise HTTPException(404, "Application not found")
    item.status = payload.status
    db.commit()
    return {"id": item.id, "status": item.status}


@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    skills = [link.skill.name for link in db.query(StudentSkill).filter_by(student_id=student.id).all()]
    text = " ".join(filter(None, [student.degree, student.branch, student.university])) + " " + " ".join(skills)
    internships = [as_dict(item) for item in db.query(Internship).filter_by(is_active=True).all()]
    vectorizer = load_vectorizer()
    if vectorizer is None:
        train_recommender(internships)
        vectorizer = load_vectorizer()
    return recommend(skills, text, student.cgpa, internships, vectorizer)


@router.post("/recommendations/retrain")
def retrain_recommender(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    internships = [as_dict(item) for item in db.query(Internship).filter_by(is_active=True).all()]
    return train_recommender(internships)
