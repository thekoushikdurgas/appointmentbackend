create table public.users
(
    id              text
        primary key,
    email           varchar(255) not null,
    hashed_password text         not null,
    name            varchar(255),
    is_active       boolean      not null default true,
    last_sign_in_at timestamp with time zone,
    created_at      timestamp with time zone not null default now(),
    updated_at      timestamp with time zone
);

alter table public.users
    owner to postgres;

create unique index idx_users_email_unique
    on public.users (email);

create index idx_users_email
    on public.users (email);

create index idx_users_id
    on public.users (id);

create index idx_users_is_active
    on public.users (is_active);

create index idx_users_created_at
    on public.users (created_at);

