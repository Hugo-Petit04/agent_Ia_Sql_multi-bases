import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # pour importer common/
from core.agent import Agent
from core.llm import schema_outil

ACTIONS_EN_ATTENTE = []

### OUTILS 

def chercher_base_donnée(sujet):
    """Transforme le texte en une requête SQL pour interroger la base de données. À remplacer par la vraie fonction."""
    return f"SELECT * FROM articles WHERE sujet = '{sujet}';"

def executer_action(description):
    """Appelée par l'interface quand l'humain clique sur Valider. À remplacer par la vraie action."""
    return f"Action exécutée (simulation) : {description}"

SCHEMA_BASE_DONNÉES = schema_outil(
    "chercher_base_donnée", "Transforme le texte en une requête SQL pour interroger la base de données.",
    {"sujet": {"type": "string", "description": "Sujet de la recherche"}})

### AGENTS

agent_recherche = Agent(
    nom="Agent recherche",
    instructions="Tu reçois du langage naturel et tu le transformes en requête SQL. "
                 "Réponds par un résumé court des faits trouvés, sans rien inventer.",
    outils=[(chercher_base_donnée, SCHEMA_BASE_DONNÉES)],
)

def creer_superviseur():
    return Agent(
        nom="Superviseur",
        instructions="Tu coordonnes une équipe d'agents. Tu ne réponds jamais de toi-même : "
                     "1) demande les faits à l'agent recherche, "  
                     "2) renvoie le texte de l'agent de recherche.",
        outils=[
            agent_recherche.comme_outil("demander_agent_recherche", "Transforme le texte en requête SQL."),
        ],
        max_iterations=8,
    )
