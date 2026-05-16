from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None


class AskResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: list[dict]


class ConversationItem(BaseModel):
    id: int
    title: str


class MessageItem(BaseModel):
    id: int
    role: str
    content: str


class BasicInfo(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class JobInfo(BaseModel):
    job_intention: str | None = None
    expected_salary: str | None = None


class BackgroundInfo(BaseModel):
    work_years: str | None = None
    education: str | None = None
    project_experience: str | None = None


class ResumeInfo(BaseModel):
    basic_info: BasicInfo
    job_info: JobInfo
    background_info: BackgroundInfo
    raw_text: str


class MatchResult(BaseModel):
    overall_score: float
    skill_match_rate: float
    experience_relevance: float
    education_match: float
    keywords_matched: list[str]
    missing_keywords: list[str]


class AnalysisResult(BaseModel):
    resume_info: ResumeInfo
    match_result: MatchResult | None = None


class AnalyzeResumeRequest(BaseModel):
    job_description: str | None = None
