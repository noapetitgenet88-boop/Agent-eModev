"""
Mémoire persistante de l'agent — biens, clients, mandats, préférences.
Sauvegardée dans memoire.json entre les sessions.
"""

import json
from datetime import datetime
from pathlib import Path

MEMOIRE_FILE = Path(__file__).parent / "memoire.json"


def charger() -> dict:
    if MEMOIRE_FILE.exists():
        try:
            with open(MEMOIRE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"biens": [], "clients": [], "notes": [], "mandats": []}


def sauvegarder(mem: dict):
    with open(MEMOIRE_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, ensure_ascii=False, indent=2)


def ajouter_note(contenu: str):
    """Ajoute une note libre à la mémoire (préférence, info marché, etc.)"""
    mem = charger()
    mem["notes"].append({"date": datetime.now().isoformat()[:10], "contenu": contenu})
    mem["notes"] = mem["notes"][-50:]  # garder les 50 dernières
    sauvegarder(mem)


def construire_contexte_memoire() -> str:
    """Génère le bloc de contexte mémoire à injecter dans le system prompt."""
    mem = charger()
    blocs = []

    if mem.get("biens"):
        blocs.append("### Biens en portefeuille\n" + "\n".join(
            f"- {b.get('ref', '?')} | {b.get('type', '')} {b.get('surface', '')}m² "
            f"| {b.get('ville', '')} | {b.get('prix', '')}€ | {b.get('statut', '')}"
            for b in mem["biens"][-20:]
        ))

    if mem.get("mandats"):
        blocs.append("### Mandats actifs\n" + "\n".join(
            f"- {m.get('ref', '?')} | Vendeur : {m.get('vendeur', '')} "
            f"| {m.get('visites', 0)} visite(s) | Signé le {m.get('date_signature', '?')}"
            for m in mem["mandats"][-20:]
        ))

    if mem.get("clients"):
        blocs.append("### Clients suivis\n" + "\n".join(
            f"- {c.get('nom', '?')} ({c.get('type', '')}) | Budget : {c.get('budget', '')}€ "
            f"| Secteur : {c.get('secteur', '')} | Statut : {c.get('statut', '')}"
            for c in mem["clients"][-20:]
        ))

    if mem.get("notes"):
        blocs.append("### Notes & préférences\n" + "\n".join(
            f"- [{n['date']}] {n['contenu']}" for n in mem["notes"][-10:]
        ))

    if not blocs:
        return ""

    return "\n\n## MA MÉMOIRE (contexte persistant)\n" + "\n\n".join(blocs)
