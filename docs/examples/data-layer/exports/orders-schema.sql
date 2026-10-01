CREATE TABLE orders (
  id integer PRIMARY KEY,
  order_no text NOT NULL,
  tenant_id text NOT NULL,
  promised_date date,
  status text NOT NULL,
  UNIQUE (order_no, tenant_id)
);
CREATE TABLE order_lines (
  id integer PRIMARY KEY,
  order_id integer NOT NULL REFERENCES orders(id),
  part_id text NOT NULL,
  qty integer NOT NULL
);
