import csv
import io
import json

import sqlparse


def formater_sql(requete):
    return sqlparse.format(requete, reindent=True, keyword_case="upper")


def lire_resultat_sql(texte):
    """Extrait les colonnes et lignes renvoyées par l'outil SQL (None si c'est une erreur)."""
    try:
        resultat = json.loads(texte)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(resultat, dict):
        return None
    if not isinstance(resultat.get("colonnes"), list) or not isinstance(resultat.get("lignes"), list):
        return None
    return resultat


def creer_csv_resultat(resultat_sql):
    sortie = io.StringIO(newline="")
    ecrivain = csv.writer(sortie)
    ecrivain.writerow(resultat_sql["colonnes"])
    ecrivain.writerows(resultat_sql["lignes"])
    return sortie.getvalue().encode("utf-8-sig")      # utf-8-sig : accents corrects dans Excel
