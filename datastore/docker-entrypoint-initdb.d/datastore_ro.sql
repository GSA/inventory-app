-- Initialization script for postgres container. This creates the read-only
-- datastore user.

-- Create the read-only datastore user
CREATE ROLE datastore_ro NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT LOGIN;
ALTER USER datastore_ro WITH PASSWORD 'pass';

-- Grant SELECT permissions to datastore (read-only permissions)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO datastore_ro;
-- Alter the default privileges so read-only user will be granted SELECT on new objects after migrations
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO datastore_ro;
