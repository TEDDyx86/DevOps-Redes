\getenv monitor_password POSTGRES_MONITOR_PASSWORD
\getenv workload_password POSTGRES_WORKLOAD_PASSWORD

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE ROLE lab_monitor LOGIN PASSWORD :'monitor_password';
GRANT CONNECT ON DATABASE lab_network TO lab_monitor;
GRANT pg_monitor TO lab_monitor;
ALTER ROLE lab_monitor SET default_transaction_read_only = on;

CREATE ROLE lab_workload LOGIN PASSWORD :'workload_password';
GRANT CONNECT ON DATABASE lab_network TO lab_workload;
GRANT USAGE ON SCHEMA public TO lab_monitor, lab_workload;

CREATE TABLE lab_items (id integer PRIMARY KEY, value bigint NOT NULL DEFAULT 0);
INSERT INTO lab_items (id) SELECT generate_series(1, 1000);
GRANT SELECT, UPDATE ON lab_items TO lab_workload;

COMMENT ON TABLE lab_items IS 'Carga real limitada a 1000 registros para demonstração acadêmica';
