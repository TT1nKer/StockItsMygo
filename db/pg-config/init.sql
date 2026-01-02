-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Set timezone
SET timezone = 'UTC';

-- Enable automatic statistics collection
ALTER DATABASE stock_db SET default_statistics_target = 100;
