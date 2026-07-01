"""Create and seed the local SQLite demo database for the Text2SQL agent."""

import sqlite3
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from real_a2a.shared import config


SCHEMA_SQL = """
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    signup_date TEXT NOT NULL
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);
"""


SEED_SQL = """
INSERT INTO customers (id, name, country, signup_date) VALUES
    (1, 'Alice Wong',    'USA',       '2024-01-15'),
    (2, 'Bruno Silva',   'Brazil',    '2024-02-02'),
    (3, 'Chika Okafor',  'Nigeria',   '2024-03-11'),
    (4, 'Divya Menon',   'India',     '2024-04-20'),
    (5, 'Erik Larsen',   'Norway',    '2024-05-05');

INSERT INTO products (id, name, category, price) VALUES
    (1, 'Basic Plan',       'subscription', 9.99),
    (2, 'Pro Plan',         'subscription', 29.99),
    (3, 'Enterprise Plan',  'subscription', 99.99),
    (4, 'Add-on: Support',  'addon',        19.99),
    (5, 'Add-on: Storage',  'addon',        4.99);

INSERT INTO orders (id, customer_id, product_id, quantity, order_date) VALUES
    (1, 1, 2, 1, '2024-06-01'),
    (2, 1, 5, 3, '2024-06-01'),
    (3, 2, 1, 1, '2024-06-05'),
    (4, 3, 3, 1, '2024-06-08'),
    (5, 3, 4, 1, '2024-06-08'),
    (6, 4, 2, 2, '2024-06-15'),
    (7, 5, 3, 1, '2024-06-20'),
    (8, 5, 5, 5, '2024-06-20');
"""


def build_seed_db(db_path: Path = config.SEED_DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()
    return db_path


if __name__ == "__main__":
    path = build_seed_db()
    print(f"Seeded database at: {path}")
