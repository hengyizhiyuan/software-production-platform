CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active');
CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, total INTEGER NOT NULL, status TEXT NOT NULL);
INSERT INTO users VALUES (1, 'Fixture User', 'user@example.invalid', 'active');
INSERT INTO customers VALUES (1, 'Fixture Customer', 'customer@example.invalid');
INSERT INTO orders VALUES (1, 1, 120, 'open');
