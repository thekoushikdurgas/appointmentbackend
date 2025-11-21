-- Drop existing table if it exists
DROP TABLE IF EXISTS companies_metadata CASCADE;

-- Create table
CREATE TABLE companies_metadata
(
    id                      bigserial
        PRIMARY KEY,
    uuid                    text,
    linkedin_url            text,
    facebook_url            text,
    twitter_url             text,
    website                 text,
    company_name_for_emails text,
    phone_number            text,
    latest_funding          text,
    latest_funding_amount   bigint,
    last_raised_at          text,
    city                    text,
    state                   text,
    country                 text
);

-- Set table owner
ALTER TABLE companies_metadata
    OWNER TO postgres;

-- Create indexes
CREATE UNIQUE INDEX idx_companies_metadata_uuid_unique
    ON companies_metadata (uuid);

