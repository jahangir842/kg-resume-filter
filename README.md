# kg-resume-filter

A **knowledge-graph-based resume filter** with explainable, graph-driven reasoning —
inspired by Palantir Gotham's ontology model.

The knowledge graph holds the logic. The LLM is only a tool: it extracts structured
entities from resume/job text and (optionally) translates questions into Cypher. It
never decides fit — graph traversals and tunable rules do, so every score is backed by
concrete graph paths instead of a black-box model.

## Architecture

```
 PDF/DOCX resume ┐                      ┌─ Cypher scoring rules (reasoning) ─┐
 + Job Desc text ┼─► LLM extraction ─► Neo4j KG ◄─ skill ontology seed       │
                 │   (Claude → JSON)    (MERGE)   (taxonomy/synonyms)        │
                 ┘                                                            ▼
                                          GraphQL API (Strawberry/FastAPI) ──► client
```

- **Neo4j + Cypher** — graph store and reasoning engine
- **Strawberry + FastAPI** — GraphQL API at `/graphql`
- **Claude** — extraction + guarded text2cypher
- **Skill ontology** (`ALIAS_OF`, `IS_A`, `REQUIRES_SKILL`, `RELATED_TO`) — the reasoning substrate

## Quickstart

```bash
cp .env.example .env          # set ANTHROPIC_API_KEY; adjust Neo4j creds if needed
uv sync --extra dev           # install deps
docker compose up -d          # start Neo4j (browser at http://localhost:7474)

uv run python -m kgrf.ontology.seed                 # constraints + skill ontology
uv run python -m kgrf.ingestion.loader data/samples/resume.txt data/samples/job.txt
uv run uvicorn kgrf.api.app:app --reload            # GraphQL at /graphql
```

Example query (GraphiQL at `http://localhost:8000/graphql`):

```graphql
query {
  fit(candidateId: "jane.doe@example.com", jobId: "senior-ml-platform-engineer-acme-ai") {
    score
    matched   { skill via contribution }
    inferred  { skill via path }
    missing
    explanation
  }
}
```

## Layout

| Path | Purpose |
|---|---|
| `src/kgrf/ontology/` | Skill taxonomy seed, constraints, `seed.py` |
| `src/kgrf/ingestion/` | Text extraction → LLM structuring → graph loader |
| `src/kgrf/reasoning/` | `queries.cypher` + `fit.py` (the scoring logic) |
| `src/kgrf/api/` | GraphQL schema + FastAPI app |
| `src/kgrf/llm/text2cypher.py` | NL → read-only Cypher (guarded) |

## Tests

```bash
uv run pytest        # reasoning tests need Neo4j up; they auto-skip if it's not
```

`tests/test_reasoning.py` seeds a known graph and asserts exact score components —
demonstrating the logic is deterministic and lives in the graph, not the LLM.

## Roadmap

- **v1 (now):** single resume ⇄ single job — explainable fit, gap analysis
- **v2:** batch ranking (many resumes vs one job), ESCO/O*NET ontology import
- **v3:** embedding-assisted skill linking as a *fallback* to the ontology
