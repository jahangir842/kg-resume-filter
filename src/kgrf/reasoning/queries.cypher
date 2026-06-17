// Named scoring queries. Blocks are delimited by "// name: <key>" headers and
// parsed by fit.py. All take $jid (job id) and $cid (candidate id).
// {HOPS} is substituted from settings.kgrf_adjacent_max_hops (config, not user input).

// name: requirements
// All REQUIRED skills of the job, with their weights — the denominator basis.
MATCH (j:JobPosting {id: $jid})-[req:REQUIRES]->(rs:Skill)
RETURN rs.name AS skill, req.weight AS weight;

// name: direct
// Candidate holds exactly the required (canonical) skill.
MATCH (j:JobPosting {id: $jid})-[req:REQUIRES]->(rs:Skill)
MATCH (c:Candidate {id: $cid})-[:HAS_SKILL]->(rs)
RETURN rs.name AS skill, req.weight AS weight, [rs.name] AS path;

// name: inferred
// Candidate holds a more-specific or prerequisite-implying skill that reaches the
// requirement via IS_A / REQUIRES_SKILL (e.g. PyTorch IS_A Deep Learning).
MATCH (j:JobPosting {id: $jid})-[req:REQUIRES]->(rs:Skill)
MATCH (c:Candidate {id: $cid})-[:HAS_SKILL]->(cs:Skill)
WHERE cs <> rs
MATCH p = (cs)-[:IS_A|REQUIRES_SKILL*1..3]->(rs)
RETURN rs.name AS skill, cs.name AS via_skill, req.weight AS weight,
       [n IN nodes(p) | n.name] AS path
ORDER BY length(p) ASC;

// name: adjacent
// Candidate holds a skill related to the requirement (partial credit), weighted by
// the product of RELATED_TO strengths along the shortest path within {HOPS} hops.
MATCH (j:JobPosting {id: $jid})-[req:REQUIRES]->(rs:Skill)
MATCH (c:Candidate {id: $cid})-[:HAS_SKILL]->(cs:Skill)
WHERE cs <> rs
MATCH p = (cs)-[:RELATED_TO*1..{HOPS}]-(rs)
RETURN rs.name AS skill, cs.name AS via_skill, req.weight AS weight,
       reduce(s = 1.0, r IN relationships(p) | s * r.strength) AS strength,
       [n IN nodes(p) | n.name] AS path
ORDER BY length(p) ASC;
