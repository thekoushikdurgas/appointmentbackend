-- Drop existing table if it exists
DROP TABLE IF EXISTS companies CASCADE;

-- Create table
CREATE TABLE companies
(
    id              bigserial
        PRIMARY KEY,
    uuid            text,
    name            text,
    employees_count bigint,
    industries      text[],
    keywords        text[],
    address         text,
    annual_revenue  bigint,
    total_funding   bigint,
    technologies    text[],
    text_search     text,
    created_at      timestamp,
    updated_at      timestamp
);

-- Set table owner
ALTER TABLE companies
    OWNER TO postgres;

-- Create indexes
CREATE UNIQUE INDEX idx_companies_uuid_unique
    ON companies (uuid);

CREATE INDEX idx_dec_trgm
    ON companies USING gin (text_search gin_trgm_ops);

CREATE INDEX idx_companies_name
    ON companies (name);

CREATE INDEX idx_companies_employees_count
    ON companies (employees_count);

CREATE INDEX idx_companies_annual_revenue
    ON companies (annual_revenue);

CREATE INDEX idx_companies_total_funding
    ON companies (total_funding);

CREATE INDEX idx_companies_industries_gin
    ON companies USING gin (industries);

CREATE INDEX idx_companies_keywords_gin
    ON companies USING gin (keywords);

CREATE INDEX idx_companies_technologies_gin
    ON companies USING gin (technologies);

CREATE INDEX idx_companies_name_trgm
    ON companies USING gin (name gin_trgm_ops);

CREATE INDEX idx_companies_created_at
    ON companies (created_at);

CREATE INDEX idx_companies_annual_revenue_industries
    ON companies (annual_revenue, industries);

