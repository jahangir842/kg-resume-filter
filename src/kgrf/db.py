"""Neo4j driver/session helpers. One process-wide driver, short-lived sessions."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

from neo4j import Driver, GraphDatabase, Session

from .config import settings


@lru_cache(maxsize=1)
def get_driver() -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


@contextmanager
def session() -> Iterator[Session]:
    drv = get_driver()
    with drv.session() as s:
        yield s


def run_write(query: str, **params: Any) -> list[dict]:
    with session() as s:
        return s.execute_write(lambda tx: [r.data() for r in tx.run(query, **params)])


def run_read(query: str, **params: Any) -> list[dict]:
    with session() as s:
        return s.execute_read(lambda tx: [r.data() for r in tx.run(query, **params)])


def close() -> None:
    get_driver().close()
    get_driver.cache_clear()
