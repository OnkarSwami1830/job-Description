CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    job_title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    salary TEXT,
    experience TEXT,
    education TEXT,
    work_mode TEXT,
    employment_type TEXT,
    job_description TEXT NOT NULL,
    improved_description TEXT,
    jd_score NUMERIC(5, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skills (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    category TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('Required', 'Preferred'))
);

CREATE INDEX IF NOT EXISTS skills_job_id_idx ON skills(job_id);
CREATE INDEX IF NOT EXISTS jobs_created_at_idx ON jobs(created_at DESC);
