CREATE TABLE categories (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    category_id INTEGER NOT NULL REFERENCES categories(id)
);

INSERT INTO categories (name) VALUES
    ('Peripherals'),
    ('Monitors'),
    ('Audio'),
    ('Cables');

INSERT INTO products (name, price, category_id) VALUES
    ('Wireless mouse',      120.00, 1),
    ('Mechanical keyboard', 450.00, 1),
    ('Mouse pad',            30.00, 1),
    ('Monitor 4K',         1200.00, 2),
    ('Monitor 24" FHD',     650.00, 2),
    ('Noise-cancelling headphones', 800.00, 3),
    ('USB microphone',      280.00, 3),
    ('HDMI cable',           25.00, 4);
