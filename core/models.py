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


class SkillMap(BaseModel):
    languages: list[Skill] = Field(default_factory=list)
    frameworks: list[Skill] = Field(default_factory=list)
    infrastructure: list[Skill] = Field(default_factory=list)
    soft_skills: list[Skill] = Field(default_factory=list)


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
    quick_wins: list[str]
    long_term: list[str]


class PortfolioProject(BaseModel):
    name: str
    description: str
    skills_demonstrated: list[str]


class LearningPath(BaseModel):
    phases: list[Phase] = Field(min_length=3, max_length=3)
    gap_analysis: GapAnalysis
    portfolio_project: PortfolioProject


# ─── Агент 4: Критик ──────────────────────────────────────────────────────────

class CriticResult(BaseModel):
    quality_score: int = Field(ge=0, le=100)
    quality_score_reason: str
    warnings: list[str]
    is_consistent: bool