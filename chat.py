"""
Interface de conversation avec l'agent immobilier de Raphaël.

Lancement :
    python chat.py

Commandes disponibles en cours de session :
    /nouveau        Démarrer une nouvelle conversation (vide l'historique)
    /docs           Lister les documents produits lors de cette session
    /quitter        Quitter
"""

import os
import sys
import json
import time
import anthropic
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from contexte_metier import SYSTEM_PROMPT
from outils import TOOLS, executer_outil

load_dotenv()

MODEL = "claude-opus-4-8"
MAX_TOKENS = 4096
DOCS_SESSION = []  # Documents produits dans cette session


# ─── Mise en forme terminal ───────────────────────────────────────────────────

GRIS   = "\033[90m"
BLANC  = "\033[97m"
BLEU   = "\033[94m"
VERT   = "\033[92m"
JAUNE  = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def ligne(char="─", n=62):
    print(GRIS + char * n + RESET)


def entete():
    os.system("clear")
    ligne("═")
    print(f"{BOLD}{BLANC}  Agent Immobilier — Raphaël Petitgenet / eModev{RESET}")
    print(f"{GRIS}  Modèle : {MODEL}   |   {datetime.now():%A %d %B %Y}{RESET}")
    ligne("═")
    print(f"{GRIS}  Commandes : /nouveau  /docs  /quitter{RESET}")
    ligne()
    print()


def afficher_agent(texte: str):
    print(f"\n{BLEU}{BOLD}Agent ›{RESET} ", end="")
    # Affichage progressif pour un rendu plus naturel
    for ligne_texte in texte.split("\n"):
        print(ligne_texte)
    print()


def afficher_outil(nom: str):
    labels = {
        "sauvegarder_document":    "Sauvegarde du document",
        "lister_documents_produits": "Lecture des documents",
        "netty_lire_mandats":      "Lecture des mandats (Netty)",
        "netty_lire_contacts":     "Lecture des contacts (Netty)",
    }
    label = labels.get(nom, nom)
    print(f"  {JAUNE}⟳  {label}...{RESET}")


def afficher_erreur(msg: str):
    print(f"\n  {JAUNE}⚠  {msg}{RESET}\n")


# ─── Boucle agentique ────────────────────────────────────────────────────────

def appeler_agent(client: anthropic.Anthropic, messages: list) -> str:
    """Envoie les messages à Claude et gère la boucle outil → réponse."""
    MAX_TENTATIVES = 3

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
                thinking={"type": "adaptive"},
            )
        except anthropic.RateLimitError:
            if tentative < MAX_TENTATIVES:
                afficher_erreur("Limite de requêtes atteinte — nouvelle tentative dans 10 secondes...")
                time.sleep(10)
                continue
            raise
        except anthropic.APIConnectionError:
            if tentative < MAX_TENTATIVES:
                afficher_erreur("Problème de connexion — nouvelle tentative dans 5 secondes...")
                time.sleep(5)
                continue
            raise
        break

    # Ajouter la réponse à l'historique
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        return _extraire_texte(response.content)

    if response.stop_reason == "tool_use":
        resultats = []
        for bloc in response.content:
            if bloc.type == "tool_use":
                afficher_outil(bloc.name)
                resultat_brut = executer_outil(bloc.name, bloc.input)
                resultats.append({
                    "type": "tool_result",
                    "tool_use_id": bloc.id,
                    "content": resultat_brut,
                })
                # Tracer les documents sauvegardés
                if bloc.name == "sauvegarder_document":
                    try:
                        data = json.loads(resultat_brut)
                        DOCS_SESSION.append(data.get("chemin", ""))
                    except Exception:
                        pass

        messages.append({"role": "user", "content": resultats})
        return appeler_agent(client, messages)  # Relance après outils

    return _extraire_texte(response.content)


def _extraire_texte(content: list) -> str:
    return "\n".join(
        bloc.text for bloc in content
        if hasattr(bloc, "text") and bloc.text
    ).strip()


# ─── Session de conversation ─────────────────────────────────────────────────

def verifier_configuration() -> bool:
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle or not cle.startswith("sk-ant-"):
        ligne()
        print(f"\n{JAUNE}Configuration requise{RESET}\n")
        print("Ta clé API Anthropic n'est pas configurée.")
        print(f"1. Ouvre le fichier : {BOLD}agent-immo/.env{RESET}")
        print("2. Colle ta clé après  ANTHROPIC_API_KEY=")
        print(f"   (récupérable sur {BOLD}console.anthropic.com{RESET} → API Keys)\n")
        return False
    return True


def boucle_conversation():
    entete()

    if not verifier_configuration():
        return

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = []

    print(f"{GRIS}  Prêt. Pose une question ou donne une tâche.{RESET}\n")

    while True:
        # Saisie utilisateur
        try:
            saisie = input(f"{BOLD}{BLANC}Toi ›{RESET}  ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{GRIS}  Session terminée.{RESET}\n")
            break

        if not saisie:
            continue

        # Commandes
        if saisie.lower() in ("/quitter", "/quit", "/exit", "quitter"):
            print(f"\n{GRIS}  Session terminée.{RESET}\n")
            break

        if saisie.lower() == "/nouveau":
            messages.clear()
            DOCS_SESSION.clear()
            entete()
            print(f"{GRIS}  Nouvelle conversation démarrée.{RESET}\n")
            continue

        if saisie.lower() == "/docs":
            if not DOCS_SESSION:
                print(f"\n{GRIS}  Aucun document produit dans cette session.{RESET}\n")
            else:
                print(f"\n{VERT}Documents produits dans cette session :{RESET}")
                for chemin in DOCS_SESSION:
                    print(f"  {GRIS}•{RESET} {Path(chemin).name}")
                print()
            continue

        # Ajouter le message utilisateur
        messages.append({"role": "user", "content": saisie})

        # Appel à l'agent
        print(f"\n{GRIS}  ...", end="", flush=True)
        try:
            reponse = appeler_agent(client, messages)
        except anthropic.AuthenticationError:
            afficher_erreur("Clé API invalide. Vérifie le fichier .env.")
            messages.pop()  # Retirer le message non traité
            continue
        except anthropic.APIError as e:
            afficher_erreur(f"Erreur API ({type(e).__name__}). Réessaie dans un moment.")
            messages.pop()
            continue
        except Exception as e:
            afficher_erreur(f"Erreur inattendue : {e}")
            messages.pop()
            continue

        print(f"\r{' '*6}\r", end="")  # Effacer le "..."
        afficher_agent(reponse)


if __name__ == "__main__":
    boucle_conversation()
