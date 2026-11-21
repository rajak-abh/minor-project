from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middleware.rate_limit import SensitiveRouteRateLimit
from app.routes import admin, analytics, assessments, auth, internships, interviews, resumes, students

app = FastAPI(title=settings.app_name, version="0.1.0", description="Student skills and internship tracking API")
app.add_middleware(SensitiveRouteRateLimit, limit=10, window_seconds=60, redis_url=settings.rate_limit_redis_url)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])
for route_module in (auth, students, internships, resumes, analytics, assessments, interviews, admin):
    app.include_router(route_module.router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "service": settings.app_name}
