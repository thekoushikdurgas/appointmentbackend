create table companies
(
    id              bigserial
        primary key,
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

alter table companies
    owner to postgres;

create unique index idx_companies_uuid_unique
    on companies (uuid);

create index idx_dec_trgm
    on companies using gin (text_search gin_trgm_ops);

create index idx_companies_name
    on companies (name);

create index idx_companies_employees_count
    on companies (employees_count);

create index idx_companies_annual_revenue
    on companies (annual_revenue);

create index idx_companies_total_funding
    on companies (total_funding);

create index idx_companies_industries_gin
    on companies using gin (industries);

create index idx_companies_keywords_gin
    on companies using gin (keywords);

create index idx_companies_technologies_gin
    on companies using gin (technologies);

create index idx_companies_name_trgm
    on companies using gin (name gin_trgm_ops);

create index idx_companies_created_at
    on companies (created_at);

create index idx_companies_annual_revenue_industries
    on companies (annual_revenue, industries);

