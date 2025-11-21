-- Drop existing table if it exists
DROP TABLE IF EXISTS public.users CASCADE;

-- Create table
CREATE TABLE public.users
(
    id              text
        PRIMARY KEY,
    email           varchar(255) NOT NULL,
    hashed_password text         NOT NULL,
    name            varchar(255),
    is_active       boolean      NOT NULL DEFAULT true,
    last_sign_in_at timestamp with time zone,
    created_at      timestamp with time zone NOT NULL DEFAULT now(),
    updated_at      timestamp with time zone
);

-- Set table owner
ALTER TABLE public.users
    OWNER TO postgres;

-- Create indexes
CREATE UNIQUE INDEX idx_users_email_unique
    ON public.users (email);

CREATE INDEX idx_users_email
    ON public.users (email);

CREATE INDEX idx_users_id
    ON public.users (id);

CREATE INDEX idx_users_is_active
    ON public.users (is_active);

CREATE INDEX idx_users_created_at
    ON public.users (created_at);

