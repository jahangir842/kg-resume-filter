"""FastAPI app mounting the GraphQL endpoint at /graphql (GraphiQL enabled).

Run:  uvicorn kgrf.api.app:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from .schema import schema

app = FastAPI(title="KG Resume Filter")
app.include_router(GraphQLRouter(schema, graphiql=True), prefix="/graphql")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
