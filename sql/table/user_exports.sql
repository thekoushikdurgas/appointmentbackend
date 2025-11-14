create type export_status as enum ('pending', 'completed', 'failed');

create table public.user_exports
(
    id            bigserial
        primary key,
    export_id     text         not null,
    user_id       text         not null,
    file_path     text,
    file_name     text,
    contact_count integer      default 0,
    contact_uuids text[],
    status        export_status not null default 'pending'::export_status,
    created_at    timestamp with time zone not null default now(),
    expires_at    timestamp with time zone,
    download_url  text,
    download_token text,
    constraint fk_user_exports_user_id
        foreign key (user_id)
            references public.users (id)
            on delete cascade
);

alter table public.user_exports
    owner to postgres;

create unique index idx_user_exports_export_id_unique
    on public.user_exports (export_id);

create index idx_user_exports_user_id
    on public.user_exports (user_id);

create index idx_user_exports_export_id
    on public.user_exports (export_id);

create index idx_user_exports_expires_at
    on public.user_exports (expires_at);

create index idx_user_exports_status
    on public.user_exports (status);

create index idx_user_exports_created_at
    on public.user_exports (created_at);

