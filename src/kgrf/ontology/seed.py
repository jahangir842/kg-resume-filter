"""Load constraints + the skill ontology (taxonomy/aliases) into Neo4j.

Run once before ingesting any resumes:  python -m kgrf.ontology.seed
Idempotent — safe to re-run.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..db import run_write

_HERE = Path(__file__).parent


def apply_constraints() -> None:
    raw = (_HERE / "constraints.cypher").read_text()
    # Drop // comment lines first so a ';' inside a comment can't split a statement.
    code = "\n".join(ln for ln in raw.splitlines() if not ln.strip().startswith("//"))
    for stmt in filter(str.strip, code.split(";")):
        run_write(stmt)


def load_skill_ontology() -> dict[str, int]:
    data = json.loads((_HERE / "skills_seed.json").read_text())
    counts: dict[str, int] = {}

    # Base skills (canonical = own name)
    run_write(
        "UNWIND $names AS n MERGE (s:Skill {name: n}) "
        "ON CREATE SET s.canonical = n",
        names=data["skills"],
    )
    counts["skills"] = len(data["skills"])

    # ALIAS_OF: alias points at the canonical skill
    run_write(
        """
        UNWIND $pairs AS p
        MERGE (a:Skill {name: p[0]}) ON CREATE SET a.canonical = p[1]
        MERGE (c:Skill {name: p[1]}) ON CREATE SET c.canonical = p[1]
        MERGE (a)-[:ALIAS_OF]->(c)
        """,
        pairs=data["alias_of"],
    )
    counts["alias_of"] = len(data["alias_of"])

    # IS_A taxonomy
    run_write(
        """
        UNWIND $pairs AS p
        MERGE (child:Skill {name: p[0]}) ON CREATE SET child.canonical = p[0]
        MERGE (parent:Skill {name: p[1]}) ON CREATE SET parent.canonical = p[1]
        MERGE (child)-[:IS_A]->(parent)
        """,
        pairs=data["is_a"],
    )
    counts["is_a"] = len(data["is_a"])

    # REQUIRES_SKILL (implied prerequisites)
    run_write(
        """
        UNWIND $pairs AS p
        MERGE (a:Skill {name: p[0]}) ON CREATE SET a.canonical = p[0]
        MERGE (b:Skill {name: p[1]}) ON CREATE SET b.canonical = p[1]
        MERGE (a)-[:REQUIRES_SKILL]->(b)
        """,
        pairs=data["requires_skill"],
    )
    counts["requires_skill"] = len(data["requires_skill"])

    # RELATED_TO (weighted, for partial credit)
    run_write(
        """
        UNWIND $triples AS t
        MERGE (a:Skill {name: t[0]}) ON CREATE SET a.canonical = t[0]
        MERGE (b:Skill {name: t[1]}) ON CREATE SET b.canonical = t[1]
        MERGE (a)-[r:RELATED_TO]->(b) SET r.strength = t[2]
        MERGE (b)-[r2:RELATED_TO]->(a) SET r2.strength = t[2]
        """,
        triples=data["related_to"],
    )
    counts["related_to"] = len(data["related_to"])

    return counts


def main() -> None:
    apply_constraints()
    counts = load_skill_ontology()
    total = run_write("MATCH (s:Skill) RETURN count(s) AS n")[0]["n"]
    print(f"Constraints applied. Loaded ontology: {counts}")
    print(f"Total Skill nodes in graph: {total}")


if __name__ == "__main__":
    main()
