-- Identity: users + one active session per user (UNIQUE user_id = a new login overwrites the old one)
CREATE TABLE IF NOT EXISTS users (
    id                  SERIAL PRIMARY KEY,
    email               VARCHAR(255) NOT NULL UNIQUE,
    password_hash       VARCHAR(128) NOT NULL,  -- PBKDF2-HMAC-SHA256, hex
    password_salt       VARCHAR(64)  NOT NULL,  -- random 16 bytes, hex
    password_iterations INTEGER      NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER     NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    token_hash   VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 of the cookie value, the raw token is never stored
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL
);

-- Cart: one working set of items per user
CREATE TABLE IF NOT EXISTS cart_items (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    UNIQUE (user_id, product_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id           SERIAL PRIMARY KEY,
    number       VARCHAR(20)    NOT NULL UNIQUE,  -- ZAM-YYYYMMDD-000001
    user_id      INTEGER        NOT NULL REFERENCES users(id),
    status       VARCHAR(10)    NOT NULL DEFAULT 'PENDING'
                 CHECK (status IN ('PENDING', 'COMPLETED', 'CANCELLED')),
    total        NUMERIC(12, 2) NOT NULL CHECK (total >= 0),
    created_at   TIMESTAMPTZ    NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

-- Snapshot of the product at checkout time: later product changes do not alter the order
-- product_id is not a foreign key: the order must survive product deletion
CREATE TABLE IF NOT EXISTS order_items (
    id           SERIAL PRIMARY KEY,
    order_id     INTEGER        NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id   INTEGER        NOT NULL,
    product_name VARCHAR(20)    NOT NULL,
    unit_price   NUMERIC(10, 2) NOT NULL,
    quantity     INTEGER        NOT NULL CHECK (quantity > 0),
    line_total   NUMERIC(12, 2) NOT NULL
);

-- Per-day counter for order numbers; UPSERT ... RETURNING makes it race-free
CREATE TABLE IF NOT EXISTS order_counters (
    day  DATE    PRIMARY KEY,
    last INTEGER NOT NULL
);

-- Idempotency-Key log: a repeated key returns the stored result instead of running the command again
CREATE TABLE IF NOT EXISTS processed_commands (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    idempotency_key VARCHAR(100) NOT NULL,
    command         VARCHAR(50)  NOT NULL,
    target          VARCHAR(50)  NOT NULL,
    result          JSONB        NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (user_id, idempotency_key)
);
