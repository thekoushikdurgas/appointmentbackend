-- Drop existing table if it exists
DROP TABLE IF EXISTS public.ai_chats CASCADE;

-- Create table
CREATE TABLE public.ai_chats
(
    id         text
        PRIMARY KEY,
    user_id    text                     NOT NULL,
    title      varchar(255) DEFAULT ''::character varying,
    messages   jsonb        DEFAULT '[]'::jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone,
    CONSTRAINT fk_ai_chats_user_id
        FOREIGN KEY (user_id)
            REFERENCES public.users (id)
            ON DELETE CASCADE
);

-- Set table owner
ALTER TABLE public.ai_chats
    OWNER TO postgres;

-- Create indexes
CREATE INDEX idx_ai_chats_user_id
    ON public.ai_chats (user_id);

CREATE INDEX idx_ai_chats_created_at
    ON public.ai_chats (created_at);

CREATE INDEX idx_ai_chats_updated_at
    ON public.ai_chats (updated_at);

