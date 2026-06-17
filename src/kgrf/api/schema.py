"""GraphQL schema. Resolvers are thin: they delegate to the Cypher reasoning in
reasoning/fit.py. GraphQL is the client interface; the logic stays in the graph.
"""

from __future__ import annotations

import strawberry

from ..reasoning.fit import compute_fit


@strawberry.type
class Match:
    skill: str
    via: str
    path: list[str]
    contribution: float


@strawberry.type
class Fit:
    candidate_id: str
    job_id: str
    score: float
    matched: list[Match]
    inferred: list[Match]
    adjacent: list[Match]
    missing: list[str]
    explanation: list[str]


def _to_match(d) -> Match:
    return Match(skill=d.skill, via=d.via, path=d.path, contribution=d.contribution)


@strawberry.type
class Query:
    @strawberry.field
    def fit(self, candidate_id: str, job_id: str) -> Fit:
        """Explainable fit of one candidate against one job, computed via graph rules."""
        r = compute_fit(candidate_id, job_id)
        return Fit(
            candidate_id=r.candidate_id,
            job_id=r.job_id,
            score=r.score,
            matched=[_to_match(d) for d in r.matched],
            inferred=[_to_match(d) for d in r.inferred],
            adjacent=[_to_match(d) for d in r.adjacent],
            missing=r.missing,
            explanation=r.explanation,
        )


schema = strawberry.Schema(query=Query)
