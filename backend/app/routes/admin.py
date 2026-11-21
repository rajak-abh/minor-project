from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database.session import get_db
from app.models.entities import Application, CompanyProfile, Internship, Notification, StudentProfile, User

router = APIRouter(prefix="/api/admin", tags=["administration"])


@router.get("/users")
def list_users(role: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    query = db.query(User)
    if role in {"student", "company", "admin"}:
        query = query.filter_by(role=role)
    result = []
    for account in query.order_by(User.created_at.desc()).all():
        name = account.student.full_name if account.student else (account.company.name if account.company else "")
        result.append({"id": account.id, "email": account.email, "role": account.role, "is_active": account.is_active, "name": name, "created_at": account.created_at})
    return result


@router.patch("/users/{user_id}/active")
def set_user_active(user_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    account = db.get(User, user_id)
    if not account:
        raise HTTPException(404, "User not found")
    if account.id == user.id and payload.get("is_active") is False:
        raise HTTPException(400, "Administrators cannot deactivate their own account")
    account.is_active = bool(payload.get("is_active"))
    db.commit()
    return {"id": account.id, "is_active": account.is_active}


@router.get("/internships")
def list_all_internships(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    return [{"id": item.id, "title": item.title, "company": item.company.name, "is_active": item.is_active, "applications": len(item.applications)} for item in db.query(Internship).order_by(Internship.created_at.desc()).all()]


@router.patch("/internships/{internship_id}/active")
def set_internship_active(internship_id: int, payload: dict, db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    item = db.get(Internship, internship_id)
    if not item:
        raise HTTPException(404, "Internship not found")
    item.is_active = bool(payload.get("is_active"))
    db.commit()
    return {"id": item.id, "is_active": item.is_active}


@router.get("/activity")
def platform_activity(db: Session = Depends(get_db), user: User = Depends(require_role("admin"))):
    return {"users": db.query(User).count(), "students": db.query(StudentProfile).count(), "companies": db.query(CompanyProfile).count(),
            "internships": db.query(Internship).count(), "applications": db.query(Application).count(), "notifications": db.query(Notification).count()}
