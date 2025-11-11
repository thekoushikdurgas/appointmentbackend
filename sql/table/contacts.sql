create table public.contacts
(
    id           bigserial
        primary key,
    uuid         text,
    first_name   text,
    last_name    text,
    company_id   text,
    email        text,
    title        text,
    departments  text[],
    mobile_phone text,
    email_status text,
    text_search  text,
    created_at   timestamp,
    updated_at   timestamp,
    seniority    text default '_'::text
);

alter table public.contacts
    owner to postgres;

create unique index idx_contacts_uuid_unique
    on public.contacts (uuid);

create index idx_contacts_first_name
    on public.contacts (first_name);

create index idx_contacts_last_name
    on public.contacts (last_name);

create index idx_contacts_company_id
    on public.contacts (company_id);

create index idx_contacts_email
    on public.contacts (email);

create index idx_contacts_mobile_phone
    on public.contacts (mobile_phone);

create index idx_contacts_email_status
    on public.contacts (email_status);

create index idx_contacts_title
    on public.contacts (title);

create index idx_contacts_title_trgm
    on public.contacts using gin (title public.gin_trgm_ops);

create index idx_contacts_email_company
    on public.contacts (email, company_id);

create index idx_contacts_name_company
    on public.contacts (first_name, last_name, company_id);

create index idx_contacts_created_at
    on public.contacts (created_at);

create index idx_contacts_seniority
    on public.contacts (seniority);

create index idx_contacts_seniority_company_id
    on public.contacts (seniority, company_id);

create index idx_contacts_departments_gin
    on public.contacts using gin (departments);

create index idx_contacts_company_department
    on public.contacts (company_id, departments);

create index idx_contacts_seniority_department
    on public.contacts (seniority, departments);

create index idx_contacts_dec_trgm
    on public.contacts using gin (text_search public.gin_trgm_ops);

