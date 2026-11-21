from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database.session import get_db
from app.models.entities import MockInterview, StudentProfile, User
from app.schemas import InterviewInput

router = APIRouter(prefix="/api/mock-interviews", tags=["mock interviews"])
BANK = {
    "technical": ["Explain the trade-offs between an array and a linked list.", "How would you design a REST API for a library?"],
    "hr": ["Tell me about a challenge you overcame.", "What kind of team helps you do your best work?"],
    "programming": ["Describe your approach to testing an edge case.", "How do you analyze the time complexity of your solution?"],
}


@router.get("/questions")
def questions(category: str = "technical", skill: str | None = None, user: User = Depends(require_role("student"))):
    normalized = category.lower()
    if normalized not in BANK:
        raise HTTPException(422, "Choose technical, HR, or programming")
    base = BANK[normalized]
    if skill:
        return {"category": normalized, "source": "question_bank", "questions": [f"How have you used {skill} in a project?", *base]}
    return {"category": normalized, "source": "question_bank", "questions": base}


@router.post("")
def save_answer(payload: InterviewInput, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    item = MockInterview(student_id=student.id, category=payload.category, question=payload.question, answer=payload.answer,
                         feedback="Question bank practice saved. Review your answer for clarity, a specific example, your actions, and the outcome.", feedback_source="question_bank")
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "feedback": item.feedback, "feedback_source": item.feedback_source}


@router.get("/history")
def history(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    return [{"id": item.id, "category": item.category, "question": item.question, "answer": item.answer,
             "feedback": item.feedback, "feedback_source": item.feedback_source, "created_at": item.created_at}
            for item in db.query(MockInterview).filter_by(student_id=student.id).order_by(MockInterview.created_at.desc()).all()]
