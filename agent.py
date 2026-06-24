"""
Agent immobilier autonome de Raphaël Petitgenet.

Usage :
    python agent.py "rédige une annonce pour une maison 4 pièces 95m² à Épinal, 175000€, jardin 600m², DPE D"
    python agent.py "compte-rendu mensuel pour le mandat M2024-001, 3 visites ce mois, retours mitigés sur le prix"
    python agent.py "mail de relance post-visite pour M. et Mme Leblanc qui ont visité la maison d'Épinal hier"
"""

import os
import sys
import json
import anthropic
from dotenv import load_dotenv

from contexte_metier import SYSTEM_PROMPT
from outils import TOOLS, executer_outil

load_dotenv()

MODEL = "claude-opus-4-8"
MAX_TOKENS = 4096


def executer_tache(demande: str, verbose: bool = True) -> str:
    """
    Lance l'agent sur une demande et retourne le résultat final.
    L'agent peut utiliser les outils autant de fois que nécessaire.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    messages = [{"role": "user", "content": demande}]

    if verbose:
        print(f"\n{'='*60}")
        print(f"Tâche : {demande[:80]}...")
        print(f"{'='*60}\n")

    # Boucle agentique : l'agent tourne jusqu'à stop_reason == "end_turn"
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            thinking={"type": "adaptive"},
        )

        # Ajouter la réponse de l'assistant à l'historique
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extraire le texte final
            texte_final = ""
            for bloc in response.content:
                if bloc.type == "text":
                    texte_final += bloc.text
            if verbose:
                print(texte_final)
            return texte_final

        if response.stop_reason == "tool_use":
            # Exécuter tous les outils demandés
            resultats_outils = []
            for bloc in response.content:
                if bloc.type == "tool_use":
                    if verbose:
                        print(f"  → Outil : {bloc.name}")
                    resultat = executer_outil(bloc.name, bloc.input)
                    resultats_outils.append({
                        "type": "tool_result",
                        "tool_use_id": bloc.id,
                        "content": resultat,
                    })

            messages.append({"role": "user", "content": resultats_outils})
            continue

        # Stop inattendu
        break

    return ""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExemples de tâches :")
        print('  python agent.py "rédige une annonce pour une maison 4p 95m² Épinal 175000€"')
        print('  python agent.py "liste mes mandats actifs"')
        print('  python agent.py "mail de relance pour M. Leblanc après sa visite d\'hier"')
        sys.exit(0)

    demande = " ".join(sys.argv[1:])
    executer_tache(demande)


if __name__ == "__main__":
    main()
