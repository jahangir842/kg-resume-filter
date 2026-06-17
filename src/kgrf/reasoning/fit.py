"""Fit reasoning. Pure graph rules + config weights — no LLM in this path.

For each REQUIRED skill we take the strongest evidence the candidate offers:
  direct  > inferred (IS_A / REQUIRES_SKILL) > adjacent (RELATED_TO, partial).
Every awarded point carries the path that justified it, so the score is auditable.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from ..config import settings
from ..db import run_read
from ..models import FitResult, MatchDetail

_QUERIES_FILE = Path(__file__).parent / "queries.cypher"
_NAME_RE = re.compile(r"^//\s*name:\s*(\w+)\s*$", re.MULTILINE)


@lru_cache(maxsize=1)
def _load_queries() -> dict[str, str]:
    """Parse queries.cypher into {name: cypher}. Strips comment lines."""
    raw = _QUERIES_FILE.read_text()
    queries: dict[str, str] = {}
    matches = list(_NAME_RE.finditer(raw))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[m.end():end]
        body = "\n".join(
            ln for ln in body.splitlines() if not ln.strip().startswith("//")
        ).strip().rstrip(";")
        queries[m.group(1)] = body
    return queries


def _q(name: str) -> str:
    cypher = _load_queries()[name]
    return cypher.replace("{HOPS}", str(settings.kgrf_adjacent_max_hops))


def compute_fit(candidate_id: str, job_id: str) -> FitResult:
    params = {"cid": candidate_id, "jid": job_id}

    requirements = run_read(_q("requirements"), **params)
    if not requirements:
        return FitResult(
            candidate_id=candidate_id,
            job_id=job_id,
            score=0.0,
            explanation=[f"Job {job_id!r} has no required skills (or does not exist)."],
        )

    direct = run_read(_q("direct"), **params)
    inferred = run_read(_q("inferred"), **params)
    adjacent = run_read(_q("adjacent"), **params)

    # Best evidence per required skill (direct beats inferred beats adjacent).
    best: dict[str, MatchDetail] = {}
    earned = 0.0

    def consider(skill: str, detail: MatchDetail, rank: int) -> None:
        prev = _rank.get(skill)
        if prev is None or rank < prev:
            best[skill] = detail
            _rank[skill] = rank

    _rank: dict[str, int] = {}

    for row in direct:
        skill, w = row["skill"], row["weight"]
        contrib = w * settings.kgrf_weight_direct
        consider(skill, MatchDetail(skill=skill, via="direct",
                                    path=row["path"], contribution=contrib), 0)

    for row in inferred:
        skill, w = row["skill"], row["weight"]
        if _rank.get(skill, 99) <= 1:
            continue
        contrib = w * settings.kgrf_weight_inferred
        via = f"inferred via {' -> '.join(row['path'])}"
        consider(skill, MatchDetail(skill=skill, via=via,
                                    path=row["path"], contribution=contrib), 1)

    for row in adjacent:
        skill, w, strength = row["skill"], row["weight"], row["strength"]
        if _rank.get(skill, 99) <= 2:
            continue
        contrib = w * settings.kgrf_weight_adjacent * strength
        via = f"adjacent ({strength:.2f}) via {' - '.join(row['path'])}"
        consider(skill, MatchDetail(skill=skill, via=via,
                                    path=row["path"], contribution=contrib), 2)

    max_attainable = sum(r["weight"] for r in requirements) * settings.kgrf_weight_direct
    earned = sum(d.contribution for d in best.values())
    score = round(earned / max_attainable, 4) if max_attainable else 0.0

    matched = [d for d in best.values() if _rank[d.skill] == 0]
    inferred_m = [d for d in best.values() if _rank[d.skill] == 1]
    adjacent_m = [d for d in best.values() if _rank[d.skill] == 2]
    missing = [r["skill"] for r in requirements if r["skill"] not in best]

    explanation = [f"Score {score:.2%} ({earned:.2f} / {max_attainable:.2f} attainable)."]
    for d in matched:
        explanation.append(f"[+{d.contribution:.2f}] {d.skill}: direct match.")
    for d in inferred_m:
        explanation.append(f"[+{d.contribution:.2f}] {d.skill}: {d.via}.")
    for d in adjacent_m:
        explanation.append(f"[+{d.contribution:.2f}] {d.skill}: {d.via}.")
    for skill in missing:
        explanation.append(f"[ gap ] {skill}: no path from any candidate skill.")

    return FitResult(
        candidate_id=candidate_id,
        job_id=job_id,
        score=score,
        matched=matched,
        inferred=inferred_m,
        adjacent=adjacent_m,
        missing=missing,
        explanation=explanation,
    )
