"""Load validated Resume/JobPosting models into Neo4j (idempotent MERGE).

Skills are linked to the existing ontology and normalized through ALIAS_OF, so a
resume that says "React.js" attaches to the canonical "React" node.
"""

from __future__ import annotations

import sys

from ..db import run_write
from ..models import JobPosting, Resume
from .extract_text import extract_text
from .llm_extract import extract_job, extract_resume


def _canonical_skill_merge() -> str:
    """Cypher fragment: given $name, return the canonical Skill node `s`.

    New skills are created as their own canonical; known aliases resolve to target.
    """
    return (
        "MERGE (raw:Skill {name: $name}) ON CREATE SET raw.canonical = $name "
        "WITH raw OPTIONAL MATCH (raw)-[:ALIAS_OF]->(canon:Skill) "
        "WITH coalesce(canon, raw) AS s "
    )


def load_resume(resume: Resume) -> None:
    run_write(
        "MERGE (c:Candidate {id: $id}) SET c.name = $name, c.email = $email",
        id=resume.candidate_id,
        name=resume.name,
        email=resume.email,
    )
    for sk in resume.skills:
        run_write(
            _canonical_skill_merge()
            + "MATCH (c:Candidate {id: $cid}) "
            + "MERGE (c)-[h:HAS_SKILL]->(s) "
            + "SET h.years = $years, h.last_used = $last_used",
            name=sk.name,
            cid=resume.candidate_id,
            years=sk.years,
            last_used=sk.last_used,
        )
    for exp in resume.experience:
        run_write(
            """
            MATCH (c:Candidate {id: $cid})
            MERGE (co:Company {name: $company})
            MERGE (e:Experience {candidate: $cid, role: $role, company: $company})
              SET e.start_year = $start, e.end_year = $end, e.summary = $summary
            MERGE (c)-[:HAD_EXPERIENCE]->(e)
            MERGE (e)-[:AT]->(co)
            """,
            cid=resume.candidate_id,
            company=exp.company,
            role=exp.role,
            start=exp.start_year,
            end=exp.end_year,
            summary=exp.summary,
        )
    for edu in resume.education:
        run_write(
            """
            MATCH (c:Candidate {id: $cid})
            MERGE (d:Degree {candidate: $cid, degree: $degree})
              SET d.level = $level, d.year = $year
            MERGE (c)-[:HOLDS]->(d)
            FOREACH (_ IN CASE WHEN $inst IS NULL THEN [] ELSE [1] END |
              MERGE (i:Institution {name: $inst})
              MERGE (d)-[:FROM]->(i))
            """,
            cid=resume.candidate_id,
            degree=edu.degree,
            level=edu.level,
            year=edu.year,
            inst=edu.institution,
        )
    for cert in resume.certifications:
        run_write(
            "MATCH (c:Candidate {id: $cid}) "
            "MERGE (cert:Certification {name: $name}) "
            "MERGE (c)-[:EARNED]->(cert)",
            cid=resume.candidate_id,
            name=cert,
        )


def load_job(job: JobPosting) -> None:
    run_write(
        "MERGE (j:JobPosting {id: $id}) "
        "SET j.title = $title, j.company = $company, j.min_degree_level = $deg",
        id=job.job_id,
        title=job.title,
        company=job.company,
        deg=job.min_degree_level,
    )
    for req in job.requirements:
        rel = "REQUIRES" if req.required else "PREFERS"
        run_write(
            _canonical_skill_merge()
            + "MATCH (j:JobPosting {id: $jid}) "
            + f"MERGE (j)-[r:{rel}]->(s) "
            + "SET r.weight = $weight, r.min_years = $min_years",
            name=req.skill,
            jid=job.job_id,
            weight=req.weight,
            min_years=req.min_years,
        )


def ingest_file(path: str, kind: str) -> str:
    """Extract -> structure -> load. kind in {'resume','job'}. Returns the node id."""
    text = extract_text(path)
    if kind == "resume":
        model = extract_resume(text)
        load_resume(model)
        return model.candidate_id
    if kind == "job":
        model = extract_job(text)
        load_job(model)
        return model.job_id
    raise ValueError(f"kind must be 'resume' or 'job', got {kind!r}")


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: python -m kgrf.ingestion.loader <resume_file> <job_file>")
        raise SystemExit(2)
    cid = ingest_file(sys.argv[1], "resume")
    jid = ingest_file(sys.argv[2], "job")
    print(f"Loaded candidate={cid} job={jid}")


if __name__ == "__main__":
    main()
