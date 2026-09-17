-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Set timezone
SET timezone = 'UTC';

-- Database-specific settings are configured by PostgreSQL defaults.  Do not
-- hard-code a database name here: this file is also used by stock_db_cn.
