"""Natural language -> Cypher (read-only), guarded.

The LLM only translates a question into a query; it never decides anything. The
generated Cypher is rejected unless it is a single, read-only statement, so a bad
generation cannot mutate the graph.
"""

from __future__ import annotations

import re

from anthropic import Anthropic

from ..config import settings
from ..db import run_read

# Schema hint kept in sync with the ontology so the model generates valid Cypher.
_SCHEMA_HINT = """
Graph schema:
(:Candidate {id,name,email})-[:HAS_SKILL {years,last_used}]->(:Skill {name,canonical})
(:Candidate)-[:HAD_EXPERIENCE]->(:Experience)-[:AT]->(:Company)
(:Candidate)-[:HOLDS]->(:Degree)-[:FROM]->(:Institution)
(:Candidate)-[:EARNED]->(:Certification)
(:JobPosting {id,title})-[:REQUIRES {weight,min_years}]->(:Skill)
(:JobPosting)-[:PREFERS]->(:Skill)
Skill ontology: (:Skill)-[:ALIAS_OF]->(:Skill), (:Skill)-[:IS_A]->(:Skill),
(:Skill)-[:REQUIRES_SKILL]->(:Skill), (:Skill)-[:RELATED_TO {strength}]->(:Skill)
"""

_PROMPT = """Translate the QUESTION into a single read-only Cypher query for this schema.
Return ONLY the Cypher, no prose, no code fences. Use MATCH/RETURN only.
{schema}
QUESTION: {question}
"""

_FORBIDDEN = re.compile(
    r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|DETACH|CALL|LOAD\s+CSV|FOREACH)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(RuntimeError):
    pass


def generate_cypher(question: str) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.kgrf_llm_model,
        max_tokens=600,
        messages=[{"role": "user",
                   "content": _PROMPT.format(schema=_SCHEMA_HINT, question=question)}],
    )
    cypher = resp.content[0].text.strip().strip("`").strip()
    if cypher.lower().startswith("cypher"):
        cypher = cypher[6:].strip()
    return cypher


def guard(cypher: str) -> str:
    if ";" in cypher.rstrip(";"):
        raise UnsafeQueryError("Only a single statement is allowed.")
    if _FORBIDDEN.search(cypher):
        raise UnsafeQueryError("Write/procedure keywords are not allowed.")
    if not re.match(r"^\s*(MATCH|WITH|UNWIND|RETURN)\b", cypher, re.IGNORECASE):
        raise UnsafeQueryError("Query must start with a read clause.")
    return cypher


def ask(question: str) -> dict:
    """NL question -> validated Cypher -> results. Returns query + rows for audit."""
    cypher = guard(generate_cypher(question))
    return {"cypher": cypher, "rows": run_read(cypher)}
