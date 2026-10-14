import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import sqlparse
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import Chrono, llm, repondre_en_direct, traces

PHRASES = {
    "executer_requete_sql": "Interroge les bases de données",
}


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


def afficher_sql_et_csv(requete_sql, resultat_sql, cle):
    """La requête formatée, puis le bouton de téléchargement du résultat."""
    if requete_sql:
        st.subheader("Requête SQL exécutée")
        st.code(formater_sql(requete_sql), language="sql")
    if requete_sql and resultat_sql is not None:
        st.download_button(
            "Télécharger le CSV",
            data=creer_csv_resultat(resultat_sql),
            file_name=f"requete_sql_{datetime.now().strftime('%Y-%m-%d_%Hh%M')}.csv",
            mime="text/csv",
            type="primary",
            key=f"csv_{cle}",
        )


st.title("Sql multi-bases : prototype d'agent")

if "messages" not in st.session_state:
    st.session_state.messages = []
for numero, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message.get("etapes"):
            with st.expander(f"A travaillé en {len(message['etapes'])} étape(s)"):
                for etape in message["etapes"]:
                    st.write("✓ " + etape)
        st.markdown(message["content"])
        afficher_sql_et_csv(message.get("requete_sql"), message.get("resultat_sql"), numero)

if question := st.chat_input("Votre question"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        boite = st.status("L'agent travaille…", expanded=True)
        etapes = []
        capture = {"requete_sql": None, "resultat_sql": None, "attend_resultat": False}

        def ecouteur(evt):
            """Appelée par core/traces.py à chaque trace de l'agent."""
            if evt["type"] == "ACTION":
                etape = PHRASES.get(evt.get("outil"), evt.get("outil"))
                etapes.append(etape)
                boite.write("✓ " + etape)
                if evt.get("outil") == "executer_requete_sql":
                    # la dernière requête est celle dont le résultat est résumé dans la réponse
                    capture["requete_sql"] = (evt.get("arguments") or {}).get("requete")
                    capture["resultat_sql"] = None
                    capture["attend_resultat"] = True
            elif evt["type"] == "OBSERVATION" and capture["attend_resultat"]:
                capture["resultat_sql"] = lire_resultat_sql(evt["texte"])
                capture["attend_resultat"] = False
            elif evt["type"] == "INFO":
                boite.write("⏳ Le service est saturé, nouvelle tentative en cours…")

        traces.definir_ecouteur(ecouteur)
        llm.nouvelle_demande()
        chrono = Chrono()
        try:
            reponse = st.write_stream(chrono.suivre(repondre_en_direct(st.session_state.messages)))
        except llm.ErreurLLM as erreur:
            boite.update(label="Erreur", state="error")
            st.error(str(erreur))
            st.stop()
        finally:
            traces.definir_ecouteur(None)
        boite.update(label=f"A travaillé {chrono.total:.0f} s", state="complete", expanded=False)

        afficher_sql_et_csv(capture["requete_sql"], capture["resultat_sql"], len(st.session_state.messages))
    st.session_state.messages.append({
        "role": "assistant", "content": reponse, "etapes": etapes,
        "requete_sql": capture["requete_sql"], "resultat_sql": capture["resultat_sql"]})