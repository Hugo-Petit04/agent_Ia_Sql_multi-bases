import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import openai
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pour importer core/
from core import llm, traces
from core.llm import chat, lire_arguments, message_assistant, message_outil
from outils import INSTRUCTIONS_SQL, SCHEMA_EXECUTER_REQUETE, executer_requete_sql

AGENT = "Superviseur"
MAX_ITERATIONS = 8

PROMPT_SYSTEME = INSTRUCTIONS_SQL

EXCUSE = "Désolé, je n'ai pas pu terminer : trop d'étapes nécessaires."


def a_completer(texte):
    """Le message jaune des autres labos, version page web."""
    st.warning(f"**À compléter :** {texte}")
    st.stop()


def _messages(conversation, prompt):
    """Le prompt système + ce que la page a gardé (on ne garde que le rôle et le texte)."""
    return [{"role": "system", "content": prompt or PROMPT_SYSTEME}] + [
        {"role": m["role"], "content": m["content"]} for m in conversation]


def _outils(outils, outils_en_plus):
    """Des couples (fonction, schéma). outils=None : les outils du superviseur (les sous-agents)."""
    if outils is None:
        outils = [(executer_requete_sql, SCHEMA_EXECUTER_REQUETE)]
    outils = list(outils) + list(outils_en_plus)
    return [schema for _, schema in outils], {schema["function"]["name"]: fonction for fonction, schema in outils}


def _executer(nom, arguments, fonctions):
    """Exécute un outil et rend son résultat en texte, en laissant les traces [ACTION] et [OBSERVATION]."""
    traces.action(AGENT, nom, arguments)
    if nom not in fonctions:
        resultat = f"Erreur : l'outil '{nom}' n'existe pas. Outils disponibles : {list(fonctions)}"
    else:
        try:
            resultat = fonctions[nom](**arguments)
        except Exception as erreur:  # mauvais arguments, panne de l'outil : on prévient le modèle au lieu de planter
            resultat = f"Erreur pendant l'exécution de {nom} : {erreur}"
    if not isinstance(resultat, str):
        resultat = json.dumps(resultat, ensure_ascii=False)
    traces.observation(AGENT, resultat)
    return resultat


def repondre(conversation, outils_en_plus=(), prompt=None, outils=None):
    """La boucle ReAct : rend la réponse finale quand elle est entièrement écrite."""
    messages = _messages(conversation, prompt)
    schemas, fonctions = _outils(outils, outils_en_plus)
    for _ in range(MAX_ITERATIONS):
        reponse = chat(messages, tools=schemas or None, agent=AGENT)
        if not reponse.tool_calls:
            return reponse.content or ""
        messages.append(message_assistant(reponse))
        for appel in reponse.tool_calls:
            resultat = _executer(appel.function.name, lire_arguments(appel), fonctions)
            messages.append(message_outil(appel, resultat))
    return EXCUSE


def repondre_en_direct(conversation, outils_en_plus=(), prompt=None, outils=None):
    """
    La même boucle, avec stream=True : un générateur qui rend le texte morceau par morceau.
    Si le fournisseur répond 429, on attend et on réessaie (comme llm.chat), tant qu'aucun texte n'a été affiché.
    """
    messages = _messages(conversation, prompt)
    schemas, fonctions = _outils(outils, outils_en_plus)
    for _ in range(MAX_ITERATIONS):
        for essai in range(len(llm.ATTENTES_429) + 1):
            debut = time.time()
            texte, appels, usage = "", {}, None      # on repart de zéro à chaque essai
            try:
                flux = llm.client().chat.completions.create(
                    model=llm.MODELE, messages=messages, tools=schemas or openai.NOT_GIVEN,
                    temperature=0.3, stream=True)
                for bloc in flux:
                    usage = _usage(bloc) or usage
                    if not bloc.choices:
                        continue
                    delta = bloc.choices[0].delta
                    if delta.content:
                        texte += delta.content
                        yield delta.content
                    for morceau in delta.tool_calls or []:
                        appel = appels.setdefault(morceau.index, {"id": "", "nom": "", "arguments": ""})
                        appel["id"] = morceau.id or appel["id"]
                        appel["nom"] += morceau.function.name or ""
                        appel["arguments"] += morceau.function.arguments or ""
                break                                 # appel réussi : on sort de la boucle d'essais
            except openai.RateLimitError:
                # si du texte est déjà affiché, réessayer le dupliquerait : on abandonne
                if texte or essai == len(llm.ATTENTES_429):
                    raise llm.ErreurLLM("Limite de débit (erreur 429) toujours atteinte après plusieurs essais. "
                                        "Attendez une minute avant de reposer la question.") from None
                attente = llm.ATTENTES_429[essai]
                traces.tracer(AGENT, "INFO", f"Erreur 429 (trop de requêtes) : nouvelle tentative dans {attente} s...")
                time.sleep(attente)
            except openai.OpenAIError as erreur:
                raise llm.ErreurLLM(f"L'appel au modèle a échoué : {erreur}") from None

        if usage:
            llm._enregistrer_usage(SimpleNamespace(usage=usage), AGENT, time.time() - debut)
        if not appels:
            return
        messages.append({"role": "assistant", "content": texte, "tool_calls": [
            {"id": a["id"], "type": "function", "function": {"name": a["nom"], "arguments": a["arguments"]}}
            for a in appels.values()]})
        for a in appels.values():
            try:
                arguments = json.loads(a["arguments"] or "{}")
            except json.JSONDecodeError:
                arguments = {}
            resultat = _executer(a["nom"], arguments if isinstance(arguments, dict) else {}, fonctions)
            messages.append({"role": "tool", "tool_call_id": a["id"], "name": a["nom"], "content": resultat})
    yield EXCUSE

def _usage(bloc):
    """Les tokens d'un appel en streaming, s'ils sont dans ce bloc (champ usage, ou x_groq chez Groq)."""
    brut = getattr(bloc, "usage", None)
    if brut is None:
        brut = ((getattr(bloc, "model_extra", None) or {}).get("x_groq") or {}).get("usage")
    if brut is None:
        return None
    lire = brut.get if isinstance(brut, dict) else lambda cle, defaut=0: getattr(brut, cle, defaut)
    return SimpleNamespace(prompt_tokens=lire("prompt_tokens", 0) or 0,
                           completion_tokens=lire("completion_tokens", 0) or 0)


class Chrono:
    """Mesure ce que l'utilisateur ressent : le temps avant le premier mot, et le temps total."""

    def __init__(self):
        self.debut = time.time()
        self.premier_mot = None
        self.total = None

    def suivre(self, generateur):
        """Laisse passer les morceaux d'un générateur en notant quand arrive le premier."""
        for morceau in generateur:
            if self.premier_mot is None:
                self.premier_mot = time.time() - self.debut
            yield morceau
        self.fin()

    def fin(self):
        self.total = time.time() - self.debut
        if self.premier_mot is None:      # réponse arrivée d'un seul coup
            self.premier_mot = self.total

    def legende(self):
        return f"Premier mot après {self.premier_mot:.1f} s · réponse complète en {self.total:.1f} s"