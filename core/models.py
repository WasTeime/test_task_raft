from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ─── Агент 1: Аналитик рынка ─────────────────────────────────────────────────

class SkillLevel(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    NICE_TO_HAVE = "nice-to-have"


class SkillTrend(str, Enum):
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"


class Skill(BaseModel):
    name: str
    level: SkillLevel
    trend: SkillTrend
    trend_reason: str

class SoftSkill(BaseModel):
    name: str
    level: SkillLevel
    trend: SkillTrend

class SkillMap(BaseModel):
    languages: list[Skill] = Field(default_factory=list)
    frameworks: list[Skill] = Field(default_factory=list)
    infrastructure: list[Skill] = Field(default_factory=list)
    soft_skills: list[SoftSkill] = Field(default_factory=list)


# ─── Агент 2: Оценщик зарплат ─────────────────────────────────────────────────

class MarketTrend(str, Enum):
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"


class SalaryRange(BaseModel):
    min: float
    median: float
    max: float


class GradeRegion(BaseModel):
    moscow: SalaryRange
    regions_rub: SalaryRange
    remote_usd: SalaryRange

class Employer(BaseModel):
    name: str
    type: str
    description: str

class SalaryTable(BaseModel):
    junior: GradeRegion
    middle: GradeRegion
    senior: GradeRegion
    lead: GradeRegion
    market_trend: MarketTrend
    market_trend_reason: str
    top_employers: list[Employer] = Field(min_length=3, max_length=5)


# ─── Агент 3: Карьерный советник ──────────────────────────────────────────────

class Resource(BaseModel):
    name: str
    type: str
    url: Optional[str] = None
    is_free: bool = True

class PhaseProject(BaseModel):
    name: str
    description: str

class Phase(BaseModel):
    name: str
    duration_days: int
    path: list[str]
    topics: list[str]
    resources: list[Resource] = Field(min_length=2)
    milestone: str
    practice_projects: list[PhaseProject] = Field(min_length=3, max_length=3)


class GapAnalysis(BaseModel):
    quick_wins: list[str] = Field(min_length=3, max_length=4)
    long_term: list[str] = Field(min_length=3, max_length=5)


class PortfolioProject(BaseModel):
    name: str
    problem: str
    user_stories: list[str] = Field(min_length=3)
    technical_challenges: list[str] = Field(min_length=2)
    skills_demonstrated: list[str]


class LearningPath(BaseModel):
    phases: list[Phase] = Field(min_length=3, max_length=3)
    gap_analysis: GapAnalysis
    portfolio_project: PortfolioProject


# ─── Агент 4: Критик ──────────────────────────────────────────────────────────
class ScoreItem(BaseModel):
    score: int = Field(ge=0, le=25)
    reason: str

class ScoreBreakdown(BaseModel):
    salary_market_match: ScoreItem
    skills_consistency: ScoreItem
    learning_path_quality: ScoreItem
    portfolio_relevance: ScoreItem

class CriticResult(BaseModel):
    score_breakdown: ScoreBreakdown
    quality_score: int = Field(ge=0, le=100)
    quality_score_reason: str
    warnings: list[str] = Field(default_factory=list)
    is_consistent: bool = True