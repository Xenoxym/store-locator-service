-- Store Locator Service — initial PostgreSQL schema
-- Matches SQLAlchemy models in app/models (stores, users, auth).
-- Apply once on an empty database, then seed roles/users via:
--   python -m scripts.seed_users
-- and load stores via:
--   python -m scripts.load_stores data/stores_1000.csv

BEGIN;

CREATE TABLE roles (
    role_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE permissions (
    permission_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE role_permissions (
    id VARCHAR(100) PRIMARY KEY,
    role_id VARCHAR(50) NOT NULL REFERENCES roles (role_id),
    permission_id VARCHAR(50) NOT NULL REFERENCES permissions (permission_id)
);

CREATE INDEX idx_role_permissions_role ON role_permissions (role_id);
CREATE INDEX idx_role_permissions_perm ON role_permissions (permission_id);

CREATE TABLE stores (
    store_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    store_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    address_street VARCHAR(255) NOT NULL,
    address_city VARCHAR(100) NOT NULL,
    address_state VARCHAR(2) NOT NULL,
    address_postal_code VARCHAR(5) NOT NULL,
    address_country VARCHAR(3) NOT NULL DEFAULT 'USA',
    phone VARCHAR(20) NOT NULL,
    hours_mon VARCHAR(20) NOT NULL,
    hours_tue VARCHAR(20) NOT NULL,
    hours_wed VARCHAR(20) NOT NULL,
    hours_thu VARCHAR(20) NOT NULL,
    hours_fri VARCHAR(20) NOT NULL,
    hours_sat VARCHAR(20) NOT NULL,
    hours_sun VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stores_lat_lon ON stores (latitude, longitude);
CREATE INDEX idx_stores_status ON stores (status);
CREATE INDEX idx_stores_store_type ON stores (store_type);
CREATE INDEX idx_stores_postal_code ON stores (address_postal_code);

CREATE TABLE store_services (
    id VARCHAR(50) PRIMARY KEY,
    store_id VARCHAR(10) NOT NULL REFERENCES stores (store_id) ON DELETE CASCADE,
    service_name VARCHAR(50) NOT NULL
);

CREATE INDEX idx_store_services_store_id ON store_services (store_id);
CREATE INDEX idx_store_services_service_name ON store_services (service_name);

CREATE TABLE users (
    user_id VARCHAR(10) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id VARCHAR(50) NOT NULL REFERENCES roles (role_id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    must_change_password BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users (email);

CREATE TABLE refresh_tokens (
    token_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(10) NOT NULL REFERENCES users (user_id),
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens (token_hash);

COMMIT;
