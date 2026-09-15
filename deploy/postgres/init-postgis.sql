-- ==============================================================================
-- REACT-X — PostgreSQL + PostGIS Initialization Script
-- ==============================================================================

-- Enforce UTF-8 and UTC Timezone
SET client_encoding = 'UTF8';
SET timezone = 'UTC';

-- Enable PostGIS spatial extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify PostGIS installation
DO $$
BEGIN
    RAISE NOTICE 'PostGIS Version: %', PostGIS_Full_Version();
END $$;
