create table public.ai_chats
(
    id         text
        primary key,
    user_id    text                     not null,
    title      varchar(255) default ''::character varying,
    messages   jsonb        default '[]'::jsonb,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone,
    constraint fk_ai_chats_user_id
        foreign key (user_id)
            references public.users (id)
            on delete cascade
);

alter table public.ai_chats
    owner to postgres;

create index idx_ai_chats_user_id
    on public.ai_chats (user_id);

create index idx_ai_chats_created_at
    on public.ai_chats (created_at);

create index idx_ai_chats_updated_at
    on public.ai_chats (updated_at);

