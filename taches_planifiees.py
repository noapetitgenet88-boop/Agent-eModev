"""
Tâches planifiées — l'agent tourne automatiquement sans intervention de Raphaël.

Lancer en arrière-plan :
    python taches_planifiees.py

Pour tester immédiatement une tâche :
    python taches_planifiees.py --test rapport_hebdo
"""

import sys
import schedule
import time
from datetime import datetime

from agent import executer_tache


def rapport_hebdomadaire():
    """Chaque lundi matin : rapport des mandats actifs + actions suggérées."""
    print(f"\n[{datetime.now():%Y-%m-%d %H:%M}] Lancement rapport hebdomadaire...")
    executer_tache(
        "Récupère mes mandats actifs depuis Netty et produis un rapport hebdomadaire synthétique : "
        "pour chaque mandat, indique le nombre de visites depuis 7 jours, les retours reçus, "
        "et propose une action concrète (relance prix, boost annonce, contact acheteur potentiel). "
        "Sauvegarde le rapport complet."
    )


def relances_acheteurs():
    """Chaque mercredi : identifier les acheteurs à relancer (visite > 7 jours sans retour)."""
    print(f"\n[{datetime.now():%Y-%m-%d %H:%M}] Relances acheteurs...")
    executer_tache(
        "Récupère mes contacts acheteurs depuis Netty. Pour ceux qui ont visité un bien "
        "il y a plus de 7 jours sans retour de leur part, rédige un mail de relance personnalisé "
        "pour chacun. Sauvegarde chaque mail séparément."
    )


def suivi_mandats_sans_visite():
    """Chaque vendredi : détecter les mandats sans visite depuis 2 semaines."""
    print(f"\n[{datetime.now():%Y-%m-%d %H:%M}] Suivi mandats sans visite...")
    executer_tache(
        "Récupère mes mandats actifs depuis Netty. Pour ceux qui n'ont eu aucune visite "
        "depuis 14 jours, produis une fiche d'analyse avec les raisons probables (prix, photos, "
        "descriptif) et propose 2-3 actions correctives. Sauvegarde la fiche."
    )


# ─────────────────────────────────────────────
# Planification
# ─────────────────────────────────────────────

def planifier():
    schedule.every().monday.at("08:00").do(rapport_hebdomadaire)
    schedule.every().wednesday.at("09:00").do(relances_acheteurs)
    schedule.every().friday.at("17:00").do(suivi_mandats_sans_visite)

    print("Agent planifié actif. Prochaines tâches :")
    for job in schedule.jobs:
        print(f"  {job}")

    while True:
        schedule.run_pending()
        time.sleep(60)


def tester(nom_tache: str):
    taches = {
        "rapport_hebdo": rapport_hebdomadaire,
        "relances_acheteurs": relances_acheteurs,
        "suivi_mandats": suivi_mandats_sans_visite,
    }
    if nom_tache not in taches:
        print(f"Tâche inconnue. Disponibles : {', '.join(taches.keys())}")
        sys.exit(1)
    taches[nom_tache]()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--test":
        tester(sys.argv[2])
    else:
        planifier()
