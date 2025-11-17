-- Create enum type for import job status
create type import_job_status as enum ('pending', 'processing', 'completed', 'failed');

-- Create contact_import_jobs table
create table public.contact_import_jobs
(
    id             bigserial
        primary key,
    job_id         text                not null,
    file_name      text                not null,
    file_path      text                not null,
    total_rows     integer             default 0,
    processed_rows integer             default 0,
    status         import_job_status  default 'pending'::import_job_status,
    error_count    integer             default 0,
    message        text,
    created_at     timestamp with time zone not null default now(),
    updated_at     timestamp with time zone not null default now(),
    completed_at   timestamp with time zone
);

alter table public.contact_import_jobs
    owner to postgres;

-- Create unique index on job_id
create unique index idx_contact_import_jobs_job_id_unique
    on public.contact_import_jobs (job_id);

-- Create index on job_id for lookups
create index idx_contact_import_jobs_job_id
    on public.contact_import_jobs (job_id);

-- Create index on status
create index idx_contact_import_jobs_status
    on public.contact_import_jobs (status);

-- Create index on created_at
create index idx_contact_import_jobs_created_at
    on public.contact_import_jobs (created_at);

-- Create contact_import_errors table
create table public.contact_import_errors
(
    id            bigserial
        primary key,
    job_id        bigint              not null,
    row_number    integer             not null,
    error_message text                not null,
    payload       text,
    created_at    timestamp with time zone not null default now(),
    constraint fk_contact_import_errors_job_id
        foreign key (job_id)
            references public.contact_import_jobs (id)
            on delete cascade
);

alter table public.contact_import_errors
    owner to postgres;

-- Create index on job_id for error lookups
create index idx_contact_import_errors_job_id
    on public.contact_import_errors (job_id);

-- Create index on created_at for error table
create index idx_contact_import_errors_created_at
    on public.contact_import_errors (created_at);

