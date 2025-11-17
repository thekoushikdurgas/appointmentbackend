create table companies_metadata
(
    id                      bigserial
        primary key,
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

alter table companies_metadata
    owner to postgres;

create unique index idx_companies_metadata_uuid_unique
    on companies_metadata (uuid);

