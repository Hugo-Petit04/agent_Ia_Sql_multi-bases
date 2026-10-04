import sqlite3

connection = sqlite3.connect("database/database.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL,
    continent TEXT,
    population INTEGER,
    pib REAL,
    life_expectancy REAL
)
""")

connection.commit()
connection.close()

print("Base de données créée !")