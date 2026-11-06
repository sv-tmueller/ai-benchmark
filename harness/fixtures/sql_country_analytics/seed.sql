-- Seed fixture for the sql-country-analytics prompt (benchmark harness).
--
-- Committed as text on purpose: the sql-exec mode builds a throwaway
-- :memory: SQLite database from this file on every grade call, so the
-- fixture can never be mutated and no binary DB blob lives in git.
--
-- The prompt states no column types. Chosen types, used consistently below:
--   customers(id INTEGER, name TEXT, country TEXT, signup_date TEXT)
--   orders(id INTEGER, customer_id INTEGER, order_date TEXT, total_amount REAL)
--   order_items(id INTEGER, order_id INTEGER, product_name TEXT, quantity INTEGER, unit_price REAL)
--
-- Seed policy (interpretation-independent answer key):
--   * no NULLs anywhere in the graded columns
--   * each order's total_amount equals the sum of its line items
--     (quantity * unit_price), so the top-product ranking is identical
--     whether 'total revenue' is read per line item or per order
--   * no product-revenue tie within any country
--   * Germany (12 orders) and France (10) qualify at >= 10 orders;
--     Spain (4) must be filtered out
--   * qualifying countries have distinct total_revenue (row order is key)

CREATE TABLE customers (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    country     TEXT NOT NULL,
    signup_date TEXT NOT NULL
);

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(id),
    order_date   TEXT NOT NULL,
    total_amount REAL NOT NULL
);

CREATE TABLE order_items (
    id           INTEGER PRIMARY KEY,
    order_id     INTEGER NOT NULL REFERENCES orders(id),
    product_name TEXT NOT NULL,
    quantity     INTEGER NOT NULL,
    unit_price   REAL NOT NULL
);

INSERT INTO customers (id, name, country, signup_date) VALUES
    (1, 'Anna', 'Germany', '2023-01-15'),
    (2, 'Bruno', 'Germany', '2023-02-20'),
    (3, 'Clara', 'Germany', '2023-03-05'),
    (4, 'Jean', 'France', '2023-01-30'),
    (5, 'Marie', 'France', '2023-04-11'),
    (6, 'Diego', 'Spain', '2023-05-02');

INSERT INTO orders (id, customer_id, order_date, total_amount) VALUES
    (1, 1, '2024-01-02', 25.00),
    (2, 2, '2024-01-05', 30.00),
    (3, 3, '2024-01-09', 17.50),
    (4, 1, '2024-01-14', 10.00),
    (5, 2, '2024-01-19', 30.00),
    (6, 3, '2024-01-23', 30.00),
    (7, 1, '2024-01-28', 50.00),
    (8, 2, '2024-02-02', 5.00),
    (9, 3, '2024-02-07', 25.00),
    (10, 1, '2024-02-12', 7.50),
    (11, 2, '2024-02-17', 20.00),
    (12, 3, '2024-02-22', 15.00),
    (13, 4, '2024-01-03', 8.00),
    (14, 5, '2024-01-08', 6.00),
    (15, 4, '2024-01-13', 6.00),
    (16, 5, '2024-01-18', 6.00),
    (17, 4, '2024-01-24', 9.00),
    (18, 5, '2024-01-29', 5.50),
    (19, 4, '2024-02-03', 3.00),
    (20, 5, '2024-02-08', 5.00),
    (21, 4, '2024-02-13', 2.00),
    (22, 5, '2024-02-18', 7.50),
    (23, 6, '2024-01-04', 12.00),
    (24, 6, '2024-01-12', 12.00),
    (25, 6, '2024-01-22', 16.00),
    (26, 6, '2024-02-01', 4.00);

INSERT INTO order_items (id, order_id, product_name, quantity, unit_price) VALUES
    (1, 1, 'Widget', 2, 10.00),
    (2, 1, 'Gadget', 1, 5.00),
    (3, 2, 'Widget', 3, 10.00),
    (4, 3, 'Gadget', 2, 5.00),
    (5, 3, 'Doohickey', 1, 7.50),
    (6, 4, 'Widget', 1, 10.00),
    (7, 5, 'Doohickey', 4, 7.50),
    (8, 6, 'Widget', 2, 10.00),
    (9, 6, 'Gadget', 2, 5.00),
    (10, 7, 'Widget', 5, 10.00),
    (11, 8, 'Gadget', 1, 5.00),
    (12, 9, 'Widget', 1, 10.00),
    (13, 9, 'Doohickey', 2, 7.50),
    (14, 10, 'Doohickey', 1, 7.50),
    (15, 11, 'Widget', 2, 10.00),
    (16, 12, 'Gadget', 3, 5.00),
    (17, 13, 'Croissant', 2, 3.00),
    (18, 13, 'Baguette', 1, 2.00),
    (19, 14, 'Baguette', 3, 2.00),
    (20, 15, 'Croissant', 1, 3.00),
    (21, 15, 'Macaron', 2, 1.50),
    (22, 16, 'Macaron', 4, 1.50),
    (23, 17, 'Croissant', 3, 3.00),
    (24, 18, 'Baguette', 2, 2.00),
    (25, 18, 'Macaron', 1, 1.50),
    (26, 19, 'Croissant', 1, 3.00),
    (27, 20, 'Macaron', 2, 1.50),
    (28, 20, 'Baguette', 1, 2.00),
    (29, 21, 'Baguette', 1, 2.00),
    (30, 22, 'Croissant', 2, 3.00),
    (31, 22, 'Macaron', 1, 1.50),
    (32, 23, 'Paella', 1, 12.00),
    (33, 24, 'Sangria', 3, 4.00),
    (34, 25, 'Paella', 1, 12.00),
    (35, 25, 'Sangria', 1, 4.00),
    (36, 26, 'Sangria', 1, 4.00);

