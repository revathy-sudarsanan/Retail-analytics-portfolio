-- schema.sql
-- Target: PostgreSQL 14+
-- Star-schema model built from the cleaned Online Retail II data.
-- order_line_items is included for completeness (the full clean grain
-- would live here in a real warehouse); this repo ships only a 20k-row
-- sample of it (see data/README.md) - the schema still reflects the
-- full production shape.

CREATE TABLE IF NOT EXISTS customers (
    customer_id        INTEGER PRIMARY KEY,
    country             TEXT NOT NULL,
    first_order_date    DATE NOT NULL,
    last_order_date     DATE NOT NULL,
    total_orders         INTEGER NOT NULL,
    total_spend          NUMERIC(12,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    invoice_no      TEXT PRIMARY KEY,
    customer_id      INTEGER NOT NULL REFERENCES customers(customer_id),
    country          TEXT NOT NULL,
    order_date       DATE NOT NULL,
    n_line_items     INTEGER NOT NULL,
    total_quantity   INTEGER NOT NULL,
    order_value      NUMERIC(12,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS order_line_items (
    invoice_no     TEXT NOT NULL REFERENCES orders(invoice_no),
    stock_code     TEXT NOT NULL,
    description    TEXT,
    quantity       INTEGER NOT NULL,
    invoice_date   TIMESTAMP NOT NULL,
    unit_price     NUMERIC(10,2) NOT NULL,
    customer_id    INTEGER NOT NULL REFERENCES customers(customer_id),
    country        TEXT NOT NULL,
    line_total     NUMERIC(12,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS top_products (
    stock_code           TEXT PRIMARY KEY,
    description          TEXT,
    total_quantity_sold  INTEGER NOT NULL,
    total_revenue        NUMERIC(12,2) NOT NULL,
    n_orders             INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_date ON orders(customer_id, order_date);
CREATE INDEX IF NOT EXISTS idx_orders_country_date  ON orders(country, order_date);
CREATE INDEX IF NOT EXISTS idx_line_items_invoice    ON order_line_items(invoice_no);
