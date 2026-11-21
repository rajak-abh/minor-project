"""Create clearly marked local development accounts, internship postings, and quiz content."""
import os

from app.core.security import hash_password
from app.database.session import Base, SessionLocal, engine
from app.models.entities import Assessment, AssessmentQuestion, CompanyProfile, Internship, InternshipSkill, Skill, StudentProfile, User


def seed():
    if os.getenv("APP_ENV", "development") != "development":
        raise RuntimeError("Seed data is restricted to APP_ENV=development")
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email="demo.student@example.test").first():
            print("Development seed already exists")
            return
        student_user = User(email="demo.student@example.test", password_hash=hash_password("DemoStudent!2026"), role="student")
        company_user = User(email="demo.company@example.test", password_hash=hash_password("DemoCompany!2026"), role="company")
        db.add_all([student_user, company_user]); db.flush()
        student = StudentProfile(user_id=student_user.id, full_name="Demo Student", branch="Computer Science", degree="B.Tech", cgpa=8.0)
        company = CompanyProfile(user_id=company_user.id, name="Demo Technology Company", location="Remote")
        db.add_all([student, company]); db.flush()
        for name in ("Python", "SQL", "Machine Learning"):
            skill = Skill(name=name)
            db.add(skill)
        db.flush()
        internship = Internship(company_id=company.id, title="Machine Learning Intern", description="Build data-driven applications with our engineering team.", location="Remote", stipend=15000, duration="3 months", min_cgpa=7.0, is_active=True)
        assessment = Assessment(title="Python Fundamentals", topic="Python", duration_minutes=15)
        db.add_all([internship, assessment]); db.flush()
        for name in ("Python", "SQL", "Machine Learning"):
            skill = db.query(Skill).filter_by(name=name).first()
            db.add(InternshipSkill(internship_id=internship.id, skill_id=skill.id))
        db.add_all([
            AssessmentQuestion(assessment_id=assessment.id, prompt="Which type is immutable?", options='["list", "dict", "tuple", "set"]', correct_answer="tuple", topic="Python"),
            AssessmentQuestion(assessment_id=assessment.id, prompt="What does len([1, 2, 3]) return?", options='["2", "3", "4", "None"]', correct_answer="3", topic="Python"),
        ])
        db.commit()
        print("Seeded demo.student@example.test / DemoStudent!2026 and demo.company@example.test / DemoCompany!2026")
        print("Development seed contains synthetic accounts and content; never use these credentials in a deployed environment.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
