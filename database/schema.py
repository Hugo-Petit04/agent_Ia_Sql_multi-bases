import sqlite3
import json


DATABASES = [
    "database/countries.db",
    "database/economy.db",
    "database/health.db"
]


def get_schema():
    schema = []

    for database in DATABASES:
        connection = sqlite3.connect(database)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
        """)

        tables = cursor.fetchall()

        for (table,) in tables:
            cursor.execute(f"PRAGMA table_info({table})")
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


schema = get_schema()

with open("schema.json", "w", encoding="utf-8") as file:
    json.dump(schema, file, indent=4, ensure_ascii=False)

print("Schéma enregistré dans schema.json")