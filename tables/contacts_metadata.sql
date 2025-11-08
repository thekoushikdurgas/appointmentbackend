create table public.contacts_metadata
(
    id                bigserial
        primary key,
    uuid              text,
    linkedin_url      text default '_'::text,
    facebook_url      text default '_'::text,
    twitter_url       text default '_'::text,
    website           text default '_'::text,
    work_direct_phone text default '_'::text,
    home_phone        text default '_'::text,
    city              text default '_'::text,
    state             text default '_'::text,
    country           text default '_'::text,
    other_phone       text default '_'::text,
    stage             text default '_'::text
);

alter table public.contacts_metadata
    owner to postgres;

create unique index idx_contacts_metadata_uuid_unique
    on public.contacts_metadata (uuid);

