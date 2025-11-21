-- Drop existing table if it exists
DROP TABLE IF EXISTS public.user_profiles CASCADE;

-- Create table
CREATE TABLE public.user_profiles
(
    id            bigserial
        PRIMARY KEY,
    user_id       text         NOT NULL,
    job_title     varchar(255),
    bio           text,
    timezone      varchar(100),
    avatar_url    text,
    notifications jsonb,
    role          varchar(50)  DEFAULT 'Member',
    created_at    timestamp with time zone NOT NULL DEFAULT now(),
    updated_at    timestamp with time zone,
    CONSTRAINT fk_user_profiles_user_id
        FOREIGN KEY (user_id)
            REFERENCES public.users (id)
            ON DELETE CASCADE
);

-- Set table owner
ALTER TABLE public.user_profiles
    OWNER TO postgres;

-- Create indexes
CREATE UNIQUE INDEX idx_user_profiles_user_id_unique
    ON public.user_profiles (user_id);

CREATE INDEX idx_user_profiles_user_id
    ON public.user_profiles (user_id);

CREATE INDEX idx_user_profiles_role
    ON public.user_profiles (role);

CREATE INDEX idx_user_profiles_created_at
    ON public.user_profiles (created_at);

