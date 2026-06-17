"""The text2cypher guard must reject any non-read query. No DB or LLM needed."""

from __future__ import annotations

import pytest

from kgrf.llm.text2cypher import UnsafeQueryError, guard


def test_allows_read_query():
    q = "MATCH (c:Candidate)-[:HAS_SKILL]->(s:Skill) RETURN c.name, s.name"
    assert guard(q) == q


@pytest.mark.parametrize("bad", [
    "MATCH (n) DETACH DELETE n",
    "CREATE (x:Skill {name:'evil'})",
    "MATCH (s:Skill) SET s.name = 'x'",
    "MATCH (n) RETURN n; DROP CONSTRAINT skill_name",
    "CALL apoc.cypher.run('...')",
    "RETURN 1 MERGE (a)",
])
def test_rejects_writes(bad):
    with pytest.raises(UnsafeQueryError):
        guard(bad)
