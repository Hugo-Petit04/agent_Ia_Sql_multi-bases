import json
import sys
import re 
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer core/
from core.agent import Agent
from core.llm import schema_outil

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"
DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"

DB_COUNTRIES = DATABASE_DIR / "countries.db"
DB_ECONOMY = DATABASE_DIR / "economy.db"
DB_HEALTH = DATABASE_DIR / "health.db"

ACTIONS_EN_ATTENTE = []

### OUTILS 

def chercher_schema(table=""):
    """Renvoie le schéma (tables, colonnes, types) lu dans schema.json.
    Si `table` est donné, ne renvoie que cette table."""
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return f"schema.json introuvable : {SCHEMA_PATH}"
    except json.JSONDecodeError as e:
        return f"schema.json invalide : {e}"

    if table:
        schema = [t for t in schema if t["table"].lower() == table.lower()]
        if not schema:
            return f"Table inconnue : {table}"

    # Format compact, plus facile à lire pour le LLM que le JSON brut
    return "\n".join(
        f"{t['table']}: " + ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
        for t in schema
    )

def executer_requete_sql(requete):
    """Exécute une requête SELECT sur les trois bases."""

    r = requete.strip().rstrip(";")

    if not r.lower().startswith("select"):
        return "Erreur : seules les requêtes SELECT sont autorisées."

    connection = sqlite3.connect(":memory:")

    try:
        connection.execute(
            "ATTACH DATABASE ? AS countries_db",
            (str(DB_COUNTRIES),)
        )

        connection.execute(
            "ATTACH DATABASE ? AS economy_db",
            (str(DB_ECONOMY),)
        )

        connection.execute(
            "ATTACH DATABASE ? AS health_db",
            (str(DB_HEALTH),)
        )

        cursor = connection.execute(r)

        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchmany(50)

        return {
            "colonnes": columns,
            "lignes": rows
        }

    except sqlite3.Error as e:
        return f"Erreur SQL : {e}"

    finally:
        connection.close()

def proposer_action(description):
    """Met une action en attente de validation humaine. N'exécute rien."""
    ACTIONS_EN_ATTENTE.append(description)
    return f"Action mise en attente de validation : {description}"

def executer_action(description):
    """Appelée par l'interface quand l'humain clique sur Valider."""
    return f"Action exécutée (simulation) : {description}"

SCHEMA_CHERCHER_SCHEMA = schema_outil(
    "chercher_schema",
    "Renvoie les tables, colonnes et types de la base. Laisser vide pour tout voir.",
    {"table": {"type": "string", "description": "Nom de la table (optionnel)"}})

SCHEMA_EXECUTER_REQUETE = schema_outil(
    "executer_requete_sql",
    "Exécute une requête SQL SELECT et renvoie les lignes. Erreur renvoyée si la requête est invalide.",
    {"requete": {"type": "string", "description": "Requête SELECT SQLite"}})

### AGENTS

agent_sql = Agent(
    nom="Agent sql",
    instructions=(
        "Tu reçois une question et un schéma. "
        "Écris une requête SELECT puis exécute-la avec l'outil. "
        "Corrige la requête en cas d'erreur. "
        "Ne dis jamais qu'une table n'existe pas avant d'avoir exécuté "
        "la requête avec l'outil.\n\n"

        "IMPORTANT : trois bases SQLite sont disponibles :\n"
        "- countries_db : table countries "
        "(id, country, continent)\n"
        "- economy_db : table economy "
        "(id, country_id, population, pib)\n"
        "- health_db : table health "
        "(id, country_id, life_expectancy)\n\n"

        "Pour accéder aux tables, utilise toujours leur nom avec "
        "le nom de la base :\n"
        "countries_db.countries\n"
        "economy_db.economy\n"
        "health_db.health\n\n"

        "Pour joindre les tables, utilise country_id :\n"
        "countries.id = economy.country_id\n"
        "countries.id = health.country_id\n\n"

        "Exemple :\n"
        "SELECT c.country, e.pib "
        "FROM countries_db.countries c "
        "JOIN economy_db.economy e ON c.id = e.country_id "
        "WHERE e.pib > 3000000;\n\n"

        "Après l'exécution, résume les résultats sans rien inventer."
    ),
    outils=[
        (executer_requete_sql, SCHEMA_EXECUTER_REQUETE),
    ],
)

agent_database = Agent(
    nom="Agent database",
    instructions="Tu décris la structure de la base à partir de l'outil de schéma.",
    outils=[(chercher_schema, SCHEMA_CHERCHER_SCHEMA)],
)

def creer_superviseur():
    return Agent(
        nom="Superviseur",
        instructions=(
            "Tu coordonnes une équipe d'agents. Tu ne réponds jamais de toi-même. "
            "1) Demande le schéma à l'agent database. "
            "2) Transmets la question de l'utilisateur ET le schéma obtenu à l'agent sql. "
            "3) Renvoie la réponse de l'agent sql telle quelle, sans la reformuler."
        ),
        outils=[
            agent_database.comme_outil(
                "demander_agent_database",
                "Renvoie les noms et types des colonnes de la base de données."),
            agent_sql.comme_outil(
                "demander_agent_sql",
                "Transforme une question en requête SQL, à partir de la question et du schéma."),
        ],
        max_iterations=8,
    )
