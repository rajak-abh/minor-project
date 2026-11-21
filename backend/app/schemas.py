from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    role: str = "student"
    full_name: str | None = None
    company_name: str | None = None


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SkillInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = "Technical"
    proficiency: int = Field(default=50, ge=0, le=100)


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    location: str | None = None
    university: str | None = None
    college: str | None = None
    degree: str | None = None
    branch: str | None = None
    current_semester: int | None = Field(default=None, ge=1, le=20)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    graduation_year: int | None = Field(default=None, ge=1950, le=2200)
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    technologies: list[str] = []
    url: str | None = None


class CertificationInput(BaseModel):
    title: str
    issuer: str | None = None
    issue_date: date | None = None
    credential_url: str | None = None


class WorkExperienceInput(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class ResumeReviewInput(BaseModel):
    profile: ProfileUpdate = Field(default_factory=ProfileUpdate)
    skills: list[SkillInput] = Field(default_factory=list)
    projects: list[ProjectInput] = Field(default_factory=list)
    certifications: list[CertificationInput] = Field(default_factory=list)
    work_experiences: list[WorkExperienceInput] = Field(default_factory=list)


class AchievementInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    achieved_on: date | None = None


class DeleteAccountInput(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class PreferencesUpdate(BaseModel):
    notifications_enabled: bool = True
    weekly_report: bool = True
    compact_mode: bool = False


class CompanyInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = None
    description: str | None = None
    location: str | None = None


class InternshipInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str
    location: str | None = None
    stipend: float | None = Field(default=None, ge=0)
    duration: str | None = None
    min_cgpa: float | None = Field(default=None, ge=0, le=10)
    deadline: date | None = None
    skills: list[str] = []


class StatusUpdate(BaseModel):
    status: str


class ApplicationInput(BaseModel):
    internship_id: int


class InterviewInput(BaseModel):
    category: str
    question: str
    answer: str = Field(min_length=1, max_length=12000)


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
