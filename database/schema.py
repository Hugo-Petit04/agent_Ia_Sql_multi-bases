import json
import sqlite3
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent   # fonctionne quel que soit le dossier courant

DATABASES = [
    "database/countries.db",
    "database/economy.db",
    "database/health.db"
]


def get_schema():
    schema = []

    for database in DATABASES:
        connection = sqlite3.connect(RACINE / database)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
        """)

        tables = cursor.fetchall()

        for (table,) in tables:
            cursor.execute(f'PRAGMA table_info("{table}")')
            columns = cursor.fetchall()

            schema.append({
                "database": database,
                "table": table,
                "columns": [
                    {
                        "name": column[1],
                        "type": column[2]
                    }
                    for column in columns
                ]
            })

        connection.close()

    return schema


if __name__ == "__main__":
    with open(RACINE / "schema.json", "w", encoding="utf-8") as file:
        json.dump(get_schema(), file, indent=4, ensure_ascii=False)

    print("Schéma enregistré dans schema.json")
