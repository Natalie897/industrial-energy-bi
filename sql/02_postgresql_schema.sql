-- PostgreSQL DWH: схема звезда + staging.
-- Выполнить в выделенной для проекта БД (например industrial_bi).
CREATE SCHEMA IF NOT EXISTS industrial_bi;
SET search_path TO industrial_bi;

CREATE TABLE IF NOT EXISTS stg_energy_readings (
    timestamp_local TIMESTAMP NOT NULL,
    usage_kwh NUMERIC(14,6) NOT NULL CHECK (usage_kwh >= 0),
    lagging_reactive_kvarh NUMERIC(14,6) NOT NULL,
    leading_reactive_kvarh NUMERIC(14,6) NOT NULL,
    co2_source_value NUMERIC(14,6) NOT NULL,
    lagging_power_factor_pct NUMERIC(9,6) NOT NULL,
    leading_power_factor_pct NUMERIC(9,6) NOT NULL,
    seconds_from_midnight INTEGER NOT NULL,
    week_status TEXT NOT NULL,
    load_type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year_num INTEGER NOT NULL,
    quarter_num INTEGER NOT NULL,
    month_num INTEGER NOT NULL,
    day_num INTEGER NOT NULL,
    weekday_num INTEGER NOT NULL,
    weekday_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL CHECK(is_weekend IN (0,1))
);
CREATE TABLE IF NOT EXISTS dim_time (
    time_key INTEGER PRIMARY KEY,
    hour_num INTEGER NOT NULL CHECK(hour_num BETWEEN 0 AND 23),
    minute_num INTEGER NOT NULL CHECK(minute_num IN (0,15,30,45)),
    time_label CHAR(5) NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_load_type (
    load_type_key INTEGER PRIMARY KEY,
    load_type TEXT NOT NULL UNIQUE,
    demo_tariff_krw_kwh NUMERIC(12,2) NOT NULL CHECK(demo_tariff_krw_kwh >= 0)
);
CREATE TABLE IF NOT EXISTS fact_energy_readings (
    reading_id BIGINT PRIMARY KEY,
    timestamp_local TIMESTAMP NOT NULL UNIQUE,
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    time_key INTEGER NOT NULL REFERENCES dim_time(time_key),
    load_type_key INTEGER NOT NULL REFERENCES dim_load_type(load_type_key),
    usage_kwh NUMERIC(14,6) NOT NULL CHECK(usage_kwh >= 0),
    lagging_reactive_kvarh NUMERIC(14,6) NOT NULL,
    leading_reactive_kvarh NUMERIC(14,6) NOT NULL,
    co2_source_value NUMERIC(14,6) NOT NULL,
    lagging_power_factor_pct NUMERIC(9,6) NOT NULL,
    leading_power_factor_pct NUMERIC(9,6) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pg_fact_date ON fact_energy_readings(date_key);
CREATE INDEX IF NOT EXISTS idx_pg_fact_load ON fact_energy_readings(load_type_key);

CREATE OR REPLACE VIEW vw_energy_enriched AS
SELECT f.reading_id, f.timestamp_local, d.full_date, d.year_num, d.quarter_num,
       d.month_num, d.weekday_num, d.weekday_name, d.is_weekend, t.hour_num,
       t.minute_num, l.load_type, l.demo_tariff_krw_kwh, f.usage_kwh,
       f.lagging_reactive_kvarh, f.leading_reactive_kvarh,
       f.co2_source_value, f.lagging_power_factor_pct, f.leading_power_factor_pct,
       ROUND(f.usage_kwh * l.demo_tariff_krw_kwh, 2) AS estimated_cost_krw
FROM fact_energy_readings f
JOIN dim_date d ON d.date_key = f.date_key
JOIN dim_time t ON t.time_key = f.time_key
JOIN dim_load_type l ON l.load_type_key = f.load_type_key;
