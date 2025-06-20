import sqlite3

conn = sqlite3.connect("gym.db")
c = conn.cursor()

# Tabelle principali
c.execute("""
CREATE TABLE IF NOT EXISTS athletes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    surname TEXT NOT NULL,
    club TEXT,
    category TEXT
)
""")


c.execute("""
CREATE TABLE IF NOT EXISTS judges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    surname TEXT NOT NULL,
    apparatus TEXT NOT NULL,
    code TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS rotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apparatus TEXT NOT NULL,
    athlete_id INTEGER NOT NULL,
    rotation_order INTEGER,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apparatus TEXT NOT NULL,
    athlete_id INTEGER NOT NULL,
    judge_id INTEGER NOT NULL,
    d REAL,
    e REAL,
    penalty REAL,
    score REAL,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id),
    FOREIGN KEY (judge_id) REFERENCES judges(id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

c.execute("""INSERT OR REPLACE INTO state (key, value) VALUES ('rotazione_corrente', '1'
)
""")

c.execute("""INSERT INTO state (key, value) VALUES ('show_final_ranking', '0')
ON CONFLICT(key) DO NOTHING
""")

conn.commit()
conn.close()
print("Database creato con successo.")
