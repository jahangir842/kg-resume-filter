"""Pydantic contracts — the validated boundary between the LLM and the graph.

The LLM emits JSON conforming to these models; nothing reaches Neo4j unvalidated.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Resume side ---------------------------------------------------------


class SkillRef(BaseModel):
    name: str = Field(..., description="Skill as written; normalized to the ontology at load time")
    years: float | None = Field(None, description="Approx years of hands-on use")
    last_used: int | None = Field(None, description="Year last used, e.g. 2025")


class Experience(BaseModel):
    role: str
    company: str
    start_year: int | None = None
    end_year: int | None = None  # None => current
    summary: str | None = None


class Education(BaseModel):
    degree: str  # e.g. "BSc Computer Science"
    level: str | None = None  # e.g. "Bachelor", "Master", "PhD"
    institution: str | None = None
    year: int | None = None


class Resume(BaseModel):
    candidate_id: str = Field(..., description="Stable id, e.g. email or generated slug")
    name: str
    email: str | None = None
    skills: list[SkillRef] = []
    experience: list[Experience] = []
    education: list[Education] = []
    certifications: list[str] = []


# --- Job side ------------------------------------------------------------


class Requirement(BaseModel):
    skill: str
    required: bool = True  # True => REQUIRES, False => PREFERS
    weight: float = 1.0
    min_years: float | None = None


class JobPosting(BaseModel):
    job_id: str
    title: str
    company: str | None = None
    min_degree_level: str | None = None  # "Bachelor" / "Master" / "PhD"
    requirements: list[Requirement] = []


# --- Reasoning output ----------------------------------------------------


class MatchDetail(BaseModel):
    skill: str
    via: str  # "direct" | "inferred:IS_A" | "adjacent:RELATED_TO" ...
    path: list[str]  # human-readable chain of skill names that justifies the match
    contribution: float  # weighted points this match added to the score


class FitResult(BaseModel):
    candidate_id: str
    job_id: str
    score: float  # 0..1 normalized
    matched: list[MatchDetail] = []
    inferred: list[MatchDetail] = []
    adjacent: list[MatchDetail] = []
    missing: list[str] = []  # required skills with no path to any candidate skill
    explanation: list[str] = []  # ordered, human-readable "why" lines
