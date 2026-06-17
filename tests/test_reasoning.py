"""Proves the fit score comes from deterministic graph rules — no LLM involved.

We seed a known candidate + job directly via the loader (bypassing extraction) and
assert exact score components.
"""

from __future__ import annotations

import pytest

from kgrf.ingestion.loader import load_job, load_resume
from kgrf.models import JobPosting, Requirement, Resume, SkillRef
from kgrf.reasoning.fit import compute_fit

from .conftest import requires_neo4j

CANDIDATE = Resume(
    candidate_id="jane@example.com",
    name="Jane Doe",
    email="jane@example.com",
    skills=[SkillRef(name=n) for n in
            ["Python", "PyTorch", "scikit-learn", "Docker", "Neo4j", "FastAPI"]],
)

JOB = JobPosting(
    job_id="senior-ml",
    title="Senior ML Platform Engineer",
    requirements=[
        Requirement(skill="Python"),
        Requirement(skill="Deep Learning"),
        Requirement(skill="Kubernetes"),
        Requirement(skill="Knowledge Graphs"),
    ],
)


@pytest.fixture
def loaded(seeded_ontology):
    load_resume(CANDIDATE)
    load_job(JOB)


@requires_neo4j
def test_fit_components(loaded):
    r = compute_fit("jane@example.com", "senior-ml")

    matched = {m.skill for m in r.matched}
    inferred = {m.skill for m in r.inferred}

    # Python is held directly.
    assert matched == {"Python"}
    # PyTorch IS_A* Deep Learning; Neo4j IS_A Knowledge Graphs.
    assert inferred == {"Deep Learning", "Knowledge Graphs"}
    # Nothing the candidate has reaches Kubernetes.
    assert r.missing == ["Kubernetes"]


@requires_neo4j
def test_fit_score(loaded):
    r = compute_fit("jane@example.com", "senior-ml")
    # earned = 1.0(Python) + 0.8(DL) + 0.8(KG) + 0(Kubernetes gap) = 2.6
    # attainable = 4 * 1.0 ; score = 2.6 / 4 = 0.65
    assert r.score == pytest.approx(0.65)


@requires_neo4j
def test_explanation_is_auditable(loaded):
    r = compute_fit("jane@example.com", "senior-ml")
    joined = "\n".join(r.explanation)
    assert "Deep Learning" in joined and "PyTorch" in joined  # path is shown
    assert any("gap" in line and "Kubernetes" in line for line in r.explanation)
