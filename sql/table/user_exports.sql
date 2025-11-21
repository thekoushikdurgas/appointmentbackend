-- Drop existing table and types if they exist
DROP TABLE IF EXISTS public.user_exports CASCADE;
DROP TYPE IF EXISTS export_status CASCADE;
DROP TYPE IF EXISTS export_type CASCADE;

-- Create enum types
CREATE TYPE export_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');
CREATE TYPE export_type AS ENUM ('contacts', 'companies');

-- Create table
CREATE TABLE public.user_exports
(
    id            bigserial
        primary key,
    export_id     text         not null,
    user_id       text         not null,
    export_type   export_type  not null default 'contacts'::export_type,
    file_path     text,
    file_name     text,
    contact_count integer      default 0,
    contact_uuids text[],
    company_count integer      default 0,
    company_uuids text[],
    linkedin_urls text[],  -- LinkedIn URLs used for LinkedIn exports (only populated for LinkedIn export type)
    status        export_status not null default 'pending'::export_status,
    created_at    timestamp with time zone not null default now(),
    expires_at    timestamp with time zone,
    download_url  text,
    download_token text,
    -- Progress tracking fields
    records_processed integer default 0,
    total_records integer default 0,
    progress_percentage double precision,
    estimated_time_remaining integer,
    error_message text,
    constraint fk_user_exports_user_id
        foreign key (user_id)
            references public.users (id)
            on delete cascade
);

-- Set table owner
ALTER TABLE public.user_exports
    OWNER TO postgres;

-- Create indexes
CREATE UNIQUE INDEX idx_user_exports_export_id_unique
    ON public.user_exports (export_id);

CREATE INDEX idx_user_exports_user_id
    ON public.user_exports (user_id);

CREATE INDEX idx_user_exports_export_id
    ON public.user_exports (export_id);

CREATE INDEX idx_user_exports_expires_at
    ON public.user_exports (expires_at);

CREATE INDEX idx_user_exports_status
    ON public.user_exports (status);

CREATE INDEX idx_user_exports_created_at
    ON public.user_exports (created_at);

CREATE INDEX idx_user_exports_export_type
    ON public.user_exports (export_type);

