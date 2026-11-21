from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MODEL_PATH = Path(__file__).resolve().parent / "artifacts" / "internship_tfidf.joblib"


def train_recommender(internships: list[dict], model_path: Path = MODEL_PATH) -> dict:
    documents = [f"{item['title']} {item['description']} {' '.join(item['skills'])}".strip() for item in internships]
    documents = [document for document in documents if document]
    if not documents:
        return {"trained": False, "reason": "No internship text is available yet", "documents": 0}
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    try:
        vectorizer.fit(documents)
    except ValueError:
        return {"trained": False, "reason": "Internship catalogue has no usable vocabulary", "documents": len(documents)}
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, model_path)
    return {"trained": True, "documents": len(documents), "features": len(vectorizer.vocabulary_), "model_path": str(model_path)}


def load_vectorizer(model_path: Path = MODEL_PATH):
    return joblib.load(model_path) if model_path.exists() else None


def recommend(student_skills: list[str], student_text: str, student_cgpa: float | None, internships: list[dict], vectorizer=None) -> list[dict]:
    """Deterministic content matching; no model fitting or random scores needed for sparse catalogues."""
    normalized = {skill.casefold().strip() for skill in student_skills}
    internship_documents = [f"{item['title']} {item['description']} {' '.join(item['skills'])}" for item in internships]
    similarities = [0.0] * len(internships)
    documents = [student_text or " "] + internship_documents
    if internships and any(text.strip() for text in documents):
        try:
            if vectorizer is None:
                matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform(documents)
                similarities = cosine_similarity(matrix[0:1], matrix[1:]).ravel().tolist()
            else:
                transformed = vectorizer.transform(documents)
                similarities = cosine_similarity(transformed[0:1], transformed[1:]).ravel().tolist()
        except ValueError:
            pass
    output = []
    for internship, similarity in zip(internships, similarities):
        required = {skill.casefold().strip() for skill in internship["skills"]}
        matched = sorted(skill for skill in internship["skills"] if skill.casefold().strip() in normalized)
        missing = sorted(skill for skill in internship["skills"] if skill.casefold().strip() not in normalized)
        skill_score = len(matched) / len(required) if required else 0.5
        eligibility = 0.0 if internship["min_cgpa"] is not None and (student_cgpa is None or student_cgpa < internship["min_cgpa"]) else 1.0
        score = 100 * eligibility * (0.7 * skill_score + 0.3 * float(similarity))
        output.append({**internship, "match_percentage": round(score), "matching_skills": matched, "missing_skills": missing,
                       "additional_skills": sorted(set(student_skills) - required), "eligible": bool(eligibility)})
    return sorted(output, key=lambda item: item["match_percentage"], reverse=True)
