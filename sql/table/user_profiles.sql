create table public.user_profiles
(
    id            bigserial
        primary key,
    user_id       text         not null,
    job_title     varchar(255),
    bio           text,
    timezone      varchar(100),
    avatar_url    text,
    notifications jsonb,
    role          varchar(50)  default 'Member',
    created_at    timestamp with time zone not null default now(),
    updated_at    timestamp with time zone,
    constraint fk_user_profiles_user_id
        foreign key (user_id)
            references public.users (id)
            on delete cascade
);

alter table public.user_profiles
    owner to postgres;

create unique index idx_user_profiles_user_id_unique
    on public.user_profiles (user_id);

create index idx_user_profiles_user_id
    on public.user_profiles (user_id);

create index idx_user_profiles_role
    on public.user_profiles (role);

create index idx_user_profiles_created_at
    on public.user_profiles (created_at);

