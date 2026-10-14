import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer core/
from core.agent import Agent
from core.llm import schema_outil

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"
DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"

# alias utilisé dans les requêtes -> fichier de la base
BASES = {
    "countries_db": DATABASE_DIR / "countries.db",
    "economy_db": DATABASE_DIR / "economy.db",
    "health_db": DATABASE_DIR / "health.db",
}
MAX_LIGNES = 50

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
        nom = table.lower().split(".")[-1]  # accepte "health" comme "health_db.health"
        schema = [t for t in schema if t["table"].lower() == nom]
        if not schema:
            return f"Table inconnue : {table}"

    # Format compact, plus facile à lire pour le LLM que le JSON brut.
    # Préfixé par l'alias de la base (ex. countries_db.countries), comme dans les requêtes.
    return "\n".join(
        f"{Path(t['database']).stem}_db.{t['table']}: "
        + ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
        for t in schema
    )


def executer_requete_sql(requete):
    """Exécute une requête SELECT sur les trois bases (ouvertes en lecture seule)."""
    r = requete.strip().rstrip(";").strip()

    if not r.lower().startswith(("select", "with")):
        return "Erreur : seules les requêtes SELECT sont autorisées."

    # uri=True permet d'attacher les bases avec mode=ro : aucune écriture possible,
    # même si la requête contient autre chose qu'un simple SELECT.
    connection = sqlite3.connect(":memory:", uri=True)
    try:
        for alias, fichier in BASES.items():
            connection.execute(f"ATTACH DATABASE ? AS {alias}", (f"{fichier.as_uri()}?mode=ro",))

        cursor = connection.execute(r)
        if cursor.description is None:
            return "Erreur : la requête ne renvoie aucune colonne (seules les requêtes SELECT sont autorisées)."

        colonnes = [description[0] for description in cursor.description]
        lignes = cursor.fetchmany(MAX_LIGNES + 1)
        resultat = {"colonnes": colonnes, "lignes": lignes[:MAX_LIGNES]}
        if len(lignes) > MAX_LIGNES:
            resultat["avertissement"] = (f"Résultat tronqué aux {MAX_LIGNES} premières lignes : "
                                         "utilise LIMIT, une agrégation ou un filtre plus précis.")
        return resultat

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
    {"table": {"type": "string", "description": "Nom de la table (optionnel)"}},
    requis=[])

SCHEMA_EXECUTER_REQUETE = schema_outil(
    "executer_requete_sql",
    "Exécute une requête SQL SELECT et renvoie les lignes. Erreur renvoyée si la requête est invalide.",
    {"requete": {"type": "string", "description": "Requête SELECT SQLite"}})

INSTRUCTIONS_SQL = (
    "Tu réponds en français aux questions sur les pays, à partir de trois bases SQLite. "
    "Écris une requête SELECT, exécute-la avec l'outil executer_requete_sql, "
    "et corrige-la en cas d'erreur. "
    "Ne dis jamais qu'une table n'existe pas avant d'avoir exécuté la requête.\n\n"

    "Tables disponibles (toujours préfixées par le nom de la base) :\n"
    "- countries_db.countries (id, country, continent)\n"
    "- economy_db.economy (id, country_id, population, pib)\n"
    "- health_db.health (id, country_id, life_expectancy)\n\n"

    "Jointures : countries.id = economy.country_id et countries.id = health.country_id.\n\n"

    "Exemple :\n"
    "SELECT c.country, e.pib FROM countries_db.countries c "
    "JOIN economy_db.economy e ON c.id = e.country_id WHERE e.pib > 3000000;\n\n"

    "Après l'exécution, résume les résultats brièvement, sans rien inventer."
)


### AGENTS

agent_sql = Agent(
    nom="Agent sql",
    instructions="Tu reçois une question et un schéma. " + INSTRUCTIONS_SQL,
    outils=[
        (executer_requete_sql, SCHEMA_EXECUTER_REQUETE),
    ],
)

agent_database = Agent(
    nom="Agent database",
    instructions="Tu décris la structure de la base à partir de l'outil de schéma.",
    outils=[(chercher_schema, SCHEMA_CHERCHER_SCHEMA)],
)

### SUPERVISEUR

INSTRUCTIONS_SUPERVISEUR = (
    "Tu coordonnes une équipe d'agents. Tu ne réponds jamais de toi-même. "
    "1) Demande le schéma à l'agent database. "
    "2) Transmets la question de l'utilisateur ET le schéma obtenu à l'agent sql. "
    "3) Renvoie la réponse de l'agent sql telle quelle, sans la reformuler."
)


def outils_superviseur():
    """Les deux sous-agents, présentés comme des outils (couples fonction, schéma)."""
    return [
        agent_database.comme_outil(
            "demander_agent_database",
            "Renvoie les noms et types des colonnes de la base de données."),
        agent_sql.comme_outil(
            "demander_agent_sql",
            "Transforme une question en requête SQL, à partir de la question et du schéma."),
    ]


def creer_superviseur():
    return Agent(
        nom="Superviseur",
        instructions=INSTRUCTIONS_SUPERVISEUR,
        outils=outils_superviseur(),
        max_iterations=8,
    )