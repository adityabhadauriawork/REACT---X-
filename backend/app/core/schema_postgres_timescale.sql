-- ============================================================================
-- SIH-1505 REACT-X PRODUCTION STORAGE SCHEMA (PostgreSQL + PostGIS + TimescaleDB)
-- ============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "timescaledb" CASCADE;

-- 2. Core Relational Entities
CREATE TABLE IF NOT EXISTS plant_operating_limits (
    id VARCHAR(64) PRIMARY KEY,
    asset_id VARCHAR(32) NOT NULL,
    chemical_id VARCHAR(32) NOT NULL,
    signal_id VARCHAR(64) NOT NULL,
    unit VARCHAR(16) NOT NULL,
    nominal_low DOUBLE PRECISION,
    nominal_high DOUBLE PRECISION,
    warning_low DOUBLE PRECISION,
    warning_high DOUBLE PRECISION,
    critical_low DOUBLE PRECISION,
    critical_high DOUBLE PRECISION,
    source_document VARCHAR(128) DEFAULT 'Plant Technical Safety Specification',
    verified_by VARCHAR(64) DEFAULT 'Chief Process Safety Engineer',
    effective_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. TimescaleDB Sensor Telemetry Hypertable
CREATE TABLE IF NOT EXISTS sensor_telemetry (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    asset_id VARCHAR(32) NOT NULL,
    signal_id VARCHAR(64) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(16) NOT NULL,
    quality VARCHAR(16) DEFAULT 'GOOD',
    source VARCHAR(64) DEFAULT 'EDGE_GATEWAY',
    source_type VARCHAR(16) DEFAULT 'PLANT',
    sequence BIGINT DEFAULT 0,
    operating_mode VARCHAR(32) DEFAULT 'NORMAL',
    severity_hint VARCHAR(16) DEFAULT 'NORMAL',
    correlation_id VARCHAR(64)
);

-- Convert to Hypertable partitioned on time (1 day chunks)
SELECT create_hypertable('sensor_telemetry', 'time', if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');

-- Create composite indexing for lightning-fast asset/signal window queries
CREATE INDEX IF NOT EXISTS idx_sensor_telemetry_asset_signal_time ON sensor_telemetry (asset_id, signal_id, time DESC);

-- Set TimescaleDB Compression Policy (Compress chunks older than 2 days)
ALTER TABLE sensor_telemetry SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'asset_id, signal_id'
);
SELECT add_compression_policy('sensor_telemetry', INTERVAL '2 days', if_not_exists => TRUE);

-- Set Data Retention Policy (Hot/Warm retention: 30 days)
SELECT add_retention_policy('sensor_telemetry', INTERVAL '30 days', if_not_exists => TRUE);

-- 4. PostGIS Spatial Entities
CREATE TABLE IF NOT EXISTS spatial_plant_assets (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    sector VARCHAR(64),
    criticality VARCHAR(16),
    location GEOMETRY(Point, 4326),
    footprint GEOMETRY(Polygon, 4326),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS spatial_environmental_receptors (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    receptor_type VARCHAR(32), -- 'WATER_BODY', 'DRAINAGE', 'SETTLEMENT', 'HIGHWAY', 'CRITICAL_INFRA'
    sensitivity_score DOUBLE PRECISION DEFAULT 1.0,
    geometry GEOMETRY(Geometry, 4326),
    description TEXT
);

-- Spatial Indexes
CREATE INDEX IF NOT EXISTS idx_spatial_plant_assets_geom ON spatial_plant_assets USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_spatial_receptors_geom ON spatial_environmental_receptors USING GIST(geometry);

-- 5. Persistent Incident Packets
CREATE TABLE IF NOT EXISTS incident_packets (
    incident_id VARCHAR(64) PRIMARY KEY,
    hazard_type VARCHAR(64) NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 1.0,
    affected_zone VARCHAR(128),
    first_detected TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(32) DEFAULT 'OPEN',
    source_asset_id VARCHAR(32),
    chemical_id VARCHAR(32),
    model_version VARCHAR(32) DEFAULT 'v2.0-Production',
    schema_version VARCHAR(16) DEFAULT '1.0.0',
    evidence_json JSONB,
    recommendations_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
