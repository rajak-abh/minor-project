import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.database.session import get_db
from app.models.entities import Assessment, AssessmentQuestion, AssessmentResult, StudentProfile, User

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


@router.get("")
def list_assessments(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    return [{"id": a.id, "title": a.title, "topic": a.topic, "duration_minutes": a.duration_minutes,
             "questions": [{"id": q.id, "prompt": q.prompt, "options": json.loads(q.options), "topic": q.topic} for q in a.questions]}
            for a in db.query(Assessment).filter_by(is_active=True).all()]


@router.post("/submit")
def submit_assessment(payload: dict, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    assessment = db.get(Assessment, payload.get("assessment_id"))
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    if not assessment or not student:
        raise HTTPException(404, "Assessment not found")
    answers = payload.get("answers", {})
    questions = assessment.questions
    if not questions:
        raise HTTPException(400, "Assessment has no questions")
    breakdown = {}
    correct = 0
    for question in questions:
        passed = str(answers.get(str(question.id), "")).strip().casefold() == question.correct_answer.strip().casefold()
        correct += int(passed)
        bucket = breakdown.setdefault(question.topic, {"correct": 0, "total": 0})
        bucket["correct"] += int(passed)
        bucket["total"] += 1
    result = AssessmentResult(student_id=student.id, assessment_id=assessment.id, score=round(100 * correct / len(questions), 1),
                              correct_count=correct, total_count=len(questions), skill_breakdown=json.dumps(breakdown))
    db.add(result)
    db.commit()
    return {"score": result.score, "correct": correct, "incorrect": len(questions) - correct, "total": len(questions), "skill_breakdown": breakdown}


@router.get("/history")
def assessment_history(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    student = db.query(StudentProfile).filter_by(user_id=user.id).first()
    results = db.query(AssessmentResult).filter_by(student_id=student.id).order_by(AssessmentResult.created_at.desc()).all()
    return [{"id": result.id, "assessment_id": result.assessment_id, "score": result.score, "correct": result.correct_count,
             "total": result.total_count, "skill_breakdown": json.loads(result.skill_breakdown), "created_at": result.created_at} for result in results]
