import sqlite3
import os

#dbcountries

connection = sqlite3.connect("database/countries.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL,
    continent TEXT
)
""")

countries = [
    ("Belgique", "Europe"),
    ("France", "Europe"),
    ("Allemagne", "Europe"),
    ("Espagne", "Europe"),
    ("Italie", "Europe"),
    ("Canada", "Amérique du Nord"),
    ("États-Unis", "Amérique du Nord"),
    ("Brésil", "Amérique du Sud"),
    ("Argentine", "Amérique du Sud"),
    ("Mexique", "Amérique du Nord"),
    ("Chine", "Asie"),
    ("Japon", "Asie"),
    ("Inde", "Asie"),
    ("Australie", "Océanie"),
    ("Afrique du Sud", "Afrique")
]

cursor.executemany("""
INSERT INTO countries (country, continent)
VALUES (?, ?)
""", countries)

connection.commit()
connection.close()

#dbeconomy

connection = sqlite3.connect("database/economy.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS economy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER NOT NULL,
    population INTEGER,
    pib REAL
)
""")

economy = [
    (1, 11800000, 650000),
    (2, 68000000, 3050000),
    (3, 84000000, 4560000),
    (4, 49000000, 1720000),
    (5, 59000000, 2310000),
    (6, 40000000, 2200000),
    (7, 335000000, 28000000),
    (8, 216000000, 2100000),
    (9, 46000000, 630000),
    (10, 129000000, 1800000),
    (11, 1410000000, 17900000),
    (12, 124000000, 4200000),
    (13, 1430000000, 3900000),
    (14, 27000000, 1700000),
    (15, 62000000, 405000)
]

cursor.executemany("""
INSERT INTO economy (country_id, population, pib)
VALUES (?, ?, ?)
""", economy)

connection.commit()
connection.close()

#dbhealth

connection = sqlite3.connect("database/health.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER NOT NULL,
    life_expectancy REAL
)
""")

health = [
    (1, 82.3),
    (2, 82.5),
    (3, 81.0),
    (4, 83.5),
    (5, 83.7),
    (6, 82.6),
    (7, 77.5),
    (8, 75.9),
    (9, 76.7),
    (10, 75.0),
    (11, 78.2),
    (12, 84.8),
    (13, 67.7),
    (14, 83.2),
    (15, 64.1)
]

cursor.executemany("""
INSERT INTO health (country_id, life_expectancy)
VALUES (?, ?)
""", health)

connection.commit()
connection.close()

#test jointure

connection = sqlite3.connect(":memory:")
cursor = connection.cursor()

cursor.execute("""
ATTACH DATABASE 'database/countries.db' AS countries_db
""")

cursor.execute("""
ATTACH DATABASE 'database/economy.db' AS economy_db
""")

cursor.execute("""
ATTACH DATABASE 'database/health.db' AS health_db
""")

cursor.execute("""
SELECT
    c.country,
    c.continent,
    e.population,
    e.pib,
    h.life_expectancy
FROM countries_db.countries AS c
JOIN economy_db.economy AS e
    ON c.id = e.country_id
JOIN health_db.health AS h
    ON c.id = h.country_id
ORDER BY e.pib DESC
""")

print("\n===== JOINTURE DES 3 BASES =====")

for row in cursor.fetchall():
    print(row)

connection.close()

print("\nBase de données créées avec succès !")