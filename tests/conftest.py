"""Shared fixtures. Tests that need Neo4j are skipped automatically when the DB
is unreachable, so `pytest` works in CI without infra and locally with `docker compose up`.
"""

from __future__ import annotations

import pytest

from kgrf.db import get_driver, run_write
from kgrf.ontology.seed import apply_constraints, load_skill_ontology


def _neo4j_available() -> bool:
    try:
        get_driver().verify_connectivity()
        return True
    except Exception:
        return False


requires_neo4j = pytest.mark.skipif(
    not _neo4j_available(), reason="Neo4j not reachable (run `docker compose up -d`)"
)


@pytest.fixture(scope="session")
def seeded_ontology():
    """A clean graph with the skill ontology loaded."""
    run_write("MATCH (n) DETACH DELETE n")
    apply_constraints()
    load_skill_ontology()
    yield
