-- PostgreSQL initialization script
-- Create default database and test tables

-- Create Vault admin user (used by Database secrets engine)
CREATE USER vault_admin WITH PASSWORD 'vault-admin-password-12345';
GRANT ALL PRIVILEGES ON DATABASE mcp_demo TO vault_admin;
GRANT ALL PRIVILEGES ON SCHEMA public TO vault_admin;
ALTER USER vault_admin WITH CREATEDB CREATEROLE;

-- Create Users table (owned by vault_admin)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE users OWNER TO vault_admin;

-- Create Products table (owned by vault_admin)
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE products OWNER TO vault_admin;

-- Create Orders table (owned by vault_admin)
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE orders OWNER TO vault_admin;

-- Insert initial data
INSERT INTO users (username, email) VALUES
    ('alice', 'alice@example.com'),
    ('bob', 'bob@example.com'),
    ('charlie', 'charlie@example.com')
ON CONFLICT (username) DO NOTHING;

INSERT INTO products (name, description, price, stock) VALUES
    ('Laptop', 'High-performance laptop', 1299.99, 10),
    ('Mouse', 'Wireless mouse', 29.99, 50),
    ('Keyboard', 'Mechanical keyboard', 89.99, 30),
    ('Monitor', '27-inch 4K monitor', 399.99, 15)
ON CONFLICT DO NOTHING;

INSERT INTO orders (user_id, product_id, quantity, total_price) VALUES
    (1, 1, 1, 1299.99),
    (1, 2, 2, 59.98),
    (2, 3, 1, 89.99),
    (2, 4, 1, 399.99)
ON CONFLICT DO NOTHING;

