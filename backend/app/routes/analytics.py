from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database.session import get_db
from app.models.entities import Application, AssessmentResult, CompanyProfile, Internship, Project, Resume, StudentProfile, StudentSkill, User
from app.ml.recommender import recommend

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/student")
def student_analytics(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
    if not profile:
        raise HTTPException(404, "Student profile not found")
    apps = db.query(Application).filter_by(student_id=profile.id).all()
    results = db.query(AssessmentResult).filter_by(student_id=profile.id).all()
    fields = (profile.full_name, profile.phone, profile.location, profile.university, profile.college, profile.degree, profile.branch, profile.current_semester, profile.cgpa, profile.graduation_year)
    completion = round(100 * sum(value not in (None, "") for value in fields) / len(fields))
    return {"total_skills": db.query(StudentSkill).filter_by(student_id=profile.id).count(), "total_projects": db.query(Project).filter_by(student_id=profile.id).count(),
            "profile_completion": completion, "total_applications": len(apps), "shortlisted_applications": sum(row.status == "Shortlisted" for row in apps),
            "selected_applications": sum(row.status == "Selected" for row in apps), "assessment_average": round(sum(row.score for row in results) / len(results), 1) if results else 0,
            "application_statuses": {status: sum(row.status == status for row in apps) for status in ("Applied", "Under Review", "Shortlisted", "Interview Scheduled", "Selected", "Rejected")},
            "assessment_history": [{"score": row.score, "created_at": row.created_at} for row in results]}


@router.get("/company")
def company_analytics(db: Session = Depends(get_db), user: User = Depends(require_role("company"))):
    company = db.query(CompanyProfile).filter_by(user_id=user.id).first()
    internships = db.query(Internship).filter_by(company_id=company.id).all()
    applications = [application for internship in internships for application in internship.applications]
    return {"total_internships": len(internships), "total_applicants": len(applications),
            "shortlisted_candidates": sum(row.status == "Shortlisted" for row in applications),
            "selected_candidates": sum(row.status == "Selected" for row in applications),
            "application_statistics": {status: sum(row.status == status for row in applications) for status in ("Applied", "Under Review", "Shortlisted", "Interview Scheduled", "Selected", "Rejected")}}


@router.get("/company/applicants")
def company_applicants(db: Session = Depends(get_db), user: User = Depends(require_role("company")), skill: str | None = None, min_cgpa: float | None = None, min_experience: int | None = None):
    company = db.query(CompanyProfile).filter_by(user_id=user.id).first()
    rows = []
    for internship in db.query(Internship).filter_by(company_id=company.id).all():
        for application in internship.applications:
            student = db.get(StudentProfile, application.student_id)
            student_skills = [link.skill.name for link in student.skills]
            if min_cgpa is not None and (student.cgpa is None or student.cgpa < min_cgpa):
                continue
            if min_experience is not None and len(student.work_experiences) < min_experience:
                continue
            if skill and skill.casefold() not in {name.casefold() for name in student_skills}:
                continue
            match = recommend(student_skills, " ".join(filter(None, [student.degree, student.branch, student.university])) + " " + " ".join(student_skills), student.cgpa,
                              [{"id": internship.id, "title": internship.title, "description": internship.description,
                                "skills": [link.skill.name for link in internship.skills], "min_cgpa": internship.min_cgpa}])[0]
            rows.append({"application_id": application.id, "status": application.status, "internship": internship.title,
                         "compatibility_score": match["match_percentage"], "matching_skills": match["matching_skills"], "missing_skills": match["missing_skills"],
                         "has_resume": db.query(Resume).filter_by(student_id=student.id).count() > 0,
                         "student": {"id": student.id, "name": student.full_name, "cgpa": student.cgpa, "skills": student_skills}})
    return rows
