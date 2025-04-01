CREATE TABLE records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    content TEXT,
    label INTEGER CHECK(label IS NULL OR label IN (0, 1, 2)) DEFAULT NULL
);
