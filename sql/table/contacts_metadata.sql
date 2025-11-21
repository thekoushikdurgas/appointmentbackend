-- Drop existing table if it exists
DROP TABLE IF EXISTS public.contacts_metadata CASCADE;

-- Create table
CREATE TABLE public.contacts_metadata
(
    id                bigserial
        PRIMARY KEY,
    uuid              text,
    linkedin_url      text DEFAULT '_'::text,
    facebook_url      text DEFAULT '_'::text,
    twitter_url       text DEFAULT '_'::text,
    website           text DEFAULT '_'::text,
    work_direct_phone text DEFAULT '_'::text,
    home_phone        text DEFAULT '_'::text,
    city              text DEFAULT '_'::text,
    state             text DEFAULT '_'::text,
    country           text DEFAULT '_'::text,
    other_phone       text DEFAULT '_'::text,
    stage             text DEFAULT '_'::text
);

-- Set table owner
ALTER TABLE public.contacts_metadata
    OWNER TO postgres;

-- Create indexes
CREATE UNIQUE INDEX idx_contacts_metadata_uuid_unique
    ON public.contacts_metadata (uuid);

