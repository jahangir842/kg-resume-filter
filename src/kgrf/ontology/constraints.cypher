// Uniqueness + lookup constraints. Each statement is split on ';' by seed.py.
CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT candidate_id IF NOT EXISTS FOR (c:Candidate) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT job_id IF NOT EXISTS FOR (j:JobPosting) REQUIRE j.id IS UNIQUE;
CREATE CONSTRAINT company_name IF NOT EXISTS FOR (co:Company) REQUIRE co.name IS UNIQUE;
CREATE CONSTRAINT institution_name IF NOT EXISTS FOR (i:Institution) REQUIRE i.name IS UNIQUE;
CREATE INDEX skill_canonical IF NOT EXISTS FOR (s:Skill) ON (s.canonical);
