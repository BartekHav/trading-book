-- Creates tables only if they don't already exist.
-- This makes the init-db command safe to run multiple times.

CREATE TABLE IF NOT EXISTS "User" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin', 'supplier', 'user')),
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "Item" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    price REAL NOT NULL DEFAULT 0,
    price_quantity INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS "Transaction" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    quantity_supplied INTEGER NOT NULL,
    cost REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES "Item" (id),
    FOREIGN KEY (supplier_id) REFERENCES "User" (id)
);

CREATE TABLE IF NOT EXISTS "LayoutCell" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    x_coord INTEGER NOT NULL,
    y_coord INTEGER NOT NULL,
    category_name TEXT,
    UNIQUE(x_coord, y_coord)
);

CREATE TABLE IF NOT EXISTS "ChangeLog" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    change_description TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES "User" (id),
    FOREIGN KEY (item_id) REFERENCES "Item" (id)
);

CREATE TABLE IF NOT EXISTS "Orders" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity_requested INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES "User" (id),
    FOREIGN KEY (item_id) REFERENCES "Item" (id)
);