create table public.departments_and_jobs
(
    id           bigserial
        primary key,
    department   text default '_'::text,
    job_function text default '_'::text,
    uuid         varchar(50) not null
);

alter table public.departments_and_jobs
    owner to postgres;

