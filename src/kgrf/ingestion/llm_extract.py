"""LLM extraction: unstructured text -> validated pydantic models.

This is the ONLY place the LLM touches resume/JD content, and its output is
immediately validated against models.py before anything reaches the graph.
The LLM structures; it does not reason about fit.
"""

from __future__ import annotations

import json

from anthropic import Anthropic

from ..config import settings
from ..models import JobPosting, Resume

_RESUME_PROMPT = """You are a strict information extractor. Extract structured data \
from the RESUME below and return ONLY JSON matching this schema:

{{
  "candidate_id": "<email if present, else a slug of the name>",
  "name": "...",
  "email": "... or null",
  "skills": [{{"name": "...", "years": <number or null>, "last_used": <year or null>}}],
  "experience": [{{"role": "...", "company": "...", "start_year": <int or null>,
                   "end_year": <int or null, null means current>, "summary": "..."}}],
  "education": [{{"degree": "...", "level": "Bachelor|Master|PhD or null",
                  "institution": "...", "year": <int or null>}}],
  "certifications": ["..."]
}}

Rules: use skill names as written; do not invent data; return null when unknown.

RESUME:
{text}
"""

_JOB_PROMPT = """You are a strict information extractor. Extract structured data from \
the JOB DESCRIPTION below and return ONLY JSON matching this schema:

{{
  "job_id": "<slug of title+company>",
  "title": "...",
  "company": "... or null",
  "min_degree_level": "Bachelor|Master|PhD or null",
  "requirements": [{{"skill": "...", "required": true|false,
                     "weight": <0..1, default 1.0>, "min_years": <number or null>}}]
}}

Rules: required=true for must-haves, false for nice-to-haves. Do not invent skills.

JOB DESCRIPTION:
{text}
"""


def _client() -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        text = text[4:] if text.lower().startswith("json") else text
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def _call(prompt: str) -> dict:
    resp = _client().messages.create(
        model=settings.kgrf_llm_model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(resp.content[0].text)


def extract_resume(text: str) -> Resume:
    return Resume.model_validate(_call(_RESUME_PROMPT.format(text=text)))


def extract_job(text: str) -> JobPosting:
    return JobPosting.model_validate(_call(_JOB_PROMPT.format(text=text)))
