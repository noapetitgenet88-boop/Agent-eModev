"""
Outils de l'agent immobilier — chaque outil produit un document prêt à l'emploi.
Quand Netty sera connecté, les outils netty_* liront/écriront dans la base de données.
"""

import json
import os
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "documents_produits"
OUTPUT_DIR.mkdir(exist_ok=True)


def _sauvegarder(type_doc: str, contenu: str, reference: str = "") -> str:
    """Sauvegarde un document produit dans le dossier local."""
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom = f"{date_str}_{type_doc}"
    if reference:
        nom += f"_{reference.replace(' ', '_')}"
    nom += ".txt"
    chemin = OUTPUT_DIR / nom
    chemin.write_text(contenu, encoding="utf-8")
    return str(chemin)


# ─────────────────────────────────────────────
# Outils disponibles pour l'agent
# ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "sauvegarder_document",
        "description": (
            "Sauvegarde un document produit (annonce, mail, compte-rendu, rapport, etc.) "
            "dans le dossier local pour que Raphaël puisse le retrouver et l'utiliser. "
            "Appeler cet outil systématiquement après avoir produit un document important."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type_document": {
                    "type": "string",
                    "description": (
                        "Type de document parmi : annonce, mail_vendeur, mail_acheteur, "
                        "compte_rendu, rapport_estimation, brief_visite, negociation, "
                        "presentation_mandat, post_reseaux_sociaux, rapport_rentabilite, "
                        "kpi_activite, fiche_crm, document_juridique"
                    ),
                },
                "contenu": {
                    "type": "string",
                    "description": "Contenu complet du document prêt à l'emploi",
                },
                "reference_bien": {
                    "type": "string",
                    "description": "Référence ou nom court du bien ou du contact concerné",
                },
            },
            "required": ["type_document", "contenu"],
        },
    },
    {
        "name": "lister_documents_produits",
        "description": "Liste les documents récemment produits par l'agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type_document": {
                    "type": "string",
                    "description": "Filtrer par type (optionnel). Laisser vide pour tout voir.",
                }
            },
            "required": [],
        },
    },
    # ── Netty (placeholder — activé quand l'API est disponible) ──────────────
    {
        "name": "netty_lire_mandats",
        "description": (
            "[NETTY] Récupère la liste des mandats actifs depuis Netty. "
            "Retourne une liste simulée si l'API n'est pas configurée."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "statut": {
                    "type": "string",
                    "enum": ["actif", "suspendu", "vendu", "tous"],
                    "description": "Filtrer par statut du mandat",
                }
            },
            "required": [],
        },
    },
    {
        "name": "netty_lire_contacts",
        "description": (
            "[NETTY] Récupère les contacts (acheteurs / vendeurs) depuis Netty. "
            "Retourne des données simulées si l'API n'est pas configurée."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type_contact": {
                    "type": "string",
                    "enum": ["acheteur", "vendeur", "tous"],
                }
            },
            "required": [],
        },
    },
]


# ─────────────────────────────────────────────
# Exécution des outils
# ─────────────────────────────────────────────

def executer_outil(nom: str, parametres: dict) -> str:
    if nom == "sauvegarder_document":
        chemin = _sauvegarder(
            parametres["type_document"],
            parametres["contenu"],
            parametres.get("reference_bien", ""),
        )
        return json.dumps({"statut": "sauvegardé", "chemin": chemin}, ensure_ascii=False)

    if nom == "lister_documents_produits":
        filtre = parametres.get("type_document", "")
        fichiers = sorted(OUTPUT_DIR.glob("*.txt"), reverse=True)[:20]
        if filtre:
            fichiers = [f for f in fichiers if filtre in f.name]
        return json.dumps(
            [f.name for f in fichiers],
            ensure_ascii=False,
        )

    if nom == "netty_lire_mandats":
        if not os.getenv("NETTY_API_KEY"):
            # Données de démonstration — remplacées par l'appel API réel
            return json.dumps([
                {"ref": "M2024-001", "bien": "Maison 5p - Épinal", "vendeur": "M. Dupont", "prix": 185000, "statut": "actif", "visites": 3},
                {"ref": "M2024-002", "bien": "Appart T3 - Remiremont", "vendeur": "Mme Martin", "prix": 98000, "statut": "actif", "visites": 1},
            ], ensure_ascii=False)
        # TODO: appel réel à l'API Netty
        return json.dumps({"erreur": "API Netty non encore implémentée"})

    if nom == "netty_lire_contacts":
        if not os.getenv("NETTY_API_KEY"):
            return json.dumps([
                {"id": "C001", "nom": "Leblanc", "type": "acheteur", "budget": 200000, "derniere_visite": "2024-01-15"},
                {"id": "C002", "nom": "Rousseau", "type": "vendeur", "bien_ref": "M2024-001"},
            ], ensure_ascii=False)
        return json.dumps({"erreur": "API Netty non encore implémentée"})

    return json.dumps({"erreur": f"Outil inconnu : {nom}"})
