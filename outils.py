"""
Outils de l'agent immobilier — chaque outil produit un document prêt à l'emploi.
Quand Netty sera connecté, les outils netty_* liront/écriront dans la base de données.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import database as db

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
    # ── Base de données Supabase ──────────────────────────────────────────────
    {
        "name": "lire_biens",
        "description": "Récupère les biens immobiliers depuis la base de données. Utiliser pour voir le portefeuille, trouver un bien, ou préparer un compte-rendu.",
        "input_schema": {
            "type": "object",
            "properties": {
                "statut": {"type": "string", "enum": ["actif", "compromis", "vendu", "suspendu", "tous"], "description": "Filtrer par statut"},
                "ville": {"type": "string", "description": "Filtrer par ville"},
            },
            "required": [],
        },
    },
    {
        "name": "ajouter_bien",
        "description": "Ajoute un nouveau bien immobilier dans la base de données.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Référence unique du bien (ex: M2025-001)"},
                "type_bien": {"type": "string", "description": "Type : maison, appartement, terrain, etc."},
                "surface": {"type": "number", "description": "Surface en m²"},
                "nb_pieces": {"type": "integer", "description": "Nombre de pièces"},
                "ville": {"type": "string", "description": "Ville"},
                "adresse": {"type": "string", "description": "Adresse complète"},
                "prix": {"type": "integer", "description": "Prix en euros"},
                "dpe": {"type": "string", "description": "Classe DPE : A, B, C, D, E, F ou G"},
                "etat": {"type": "string", "description": "État : bon, travaux, refait à neuf"},
                "description": {"type": "string", "description": "Description du bien"},
                "points_forts": {"type": "string", "description": "Points forts du bien"},
            },
            "required": ["reference", "type_bien", "ville"],
        },
    },
    {
        "name": "lire_contacts",
        "description": "Récupère les contacts (acheteurs et vendeurs) depuis la base de données.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type_contact": {"type": "string", "enum": ["acheteur", "vendeur", "les deux", "tous"], "description": "Type de contact"},
            },
            "required": [],
        },
    },
    {
        "name": "ajouter_contact",
        "description": "Ajoute un nouveau contact (acheteur ou vendeur) dans la base de données.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nom": {"type": "string", "description": "Nom du contact"},
                "prenom": {"type": "string", "description": "Prénom"},
                "telephone": {"type": "string", "description": "Téléphone"},
                "email": {"type": "string", "description": "Email"},
                "type_contact": {"type": "string", "enum": ["acheteur", "vendeur", "les deux"], "description": "Type de contact"},
                "budget_min": {"type": "integer", "description": "Budget minimum en euros (acheteur)"},
                "budget_max": {"type": "integer", "description": "Budget maximum en euros (acheteur)"},
                "type_bien_recherche": {"type": "string", "description": "Type de bien recherché (acheteur)"},
                "surface_min": {"type": "integer", "description": "Surface minimum souhaitée en m²"},
                "nb_pieces_min": {"type": "integer", "description": "Nombre de pièces minimum"},
                "villes_recherchees": {"type": "string", "description": "Villes recherchées, séparées par des virgules"},
                "financement": {"type": "string", "description": "Type de financement : comptant, prêt, en cours"},
                "delai": {"type": "string", "description": "Délai d'achat souhaité"},
                "notes": {"type": "string", "description": "Notes libres sur le contact"},
            },
            "required": ["nom", "type_contact"],
        },
    },
    {
        "name": "matcher_bien_acheteurs",
        "description": "Trouve les acheteurs dont les critères correspondent à un bien donné. Utiliser quand on rentre un nouveau bien pour identifier les acheteurs potentiels.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bien_id": {"type": "integer", "description": "ID du bien dans la base de données"},
            },
            "required": ["bien_id"],
        },
    },
    {
        "name": "matcher_acheteur_biens",
        "description": "Trouve les biens disponibles qui correspondent aux critères d'un acheteur. Utiliser pour proposer des biens à un acheteur.",
        "input_schema": {
            "type": "object",
            "properties": {
                "acheteur_id": {"type": "integer", "description": "ID de l'acheteur dans la base de données"},
            },
            "required": ["acheteur_id"],
        },
    },
    {
        "name": "lire_mandats",
        "description": "Récupère les mandats depuis la base de données avec les informations du bien et du vendeur.",
        "input_schema": {
            "type": "object",
            "properties": {
                "statut": {"type": "string", "enum": ["actif", "expiré", "tous"], "description": "Filtrer par statut"},
            },
            "required": [],
        },
    },
    {
        "name": "ajouter_visite",
        "description": "Enregistre une visite dans la base de données.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bien_id": {"type": "integer", "description": "ID du bien visité"},
                "acheteur_id": {"type": "integer", "description": "ID de l'acheteur"},
                "date_visite": {"type": "string", "description": "Date de la visite (YYYY-MM-DD)"},
                "avis_acheteur": {"type": "string", "description": "Retour de l'acheteur"},
                "points_positifs": {"type": "string", "description": "Points positifs relevés"},
                "points_negatifs": {"type": "string", "description": "Points négatifs relevés"},
                "suite_donnee": {"type": "string", "description": "Suite donnée : en attente, intéressé, pas intéressé, offre en cours"},
                "notes": {"type": "string", "description": "Notes libres"},
            },
            "required": ["bien_id", "date_visite"],
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

    if nom == "lire_biens":
        statut = parametres.get("statut", "actif")
        ville = parametres.get("ville", "")
        data = db.chercher_biens(ville=ville) if ville else db.lire_biens(statut=statut)
        return json.dumps(data, ensure_ascii=False, default=str)

    if nom == "ajouter_bien":
        data = db.ajouter_bien(parametres)
        return json.dumps({"statut": "bien ajouté", "data": data}, ensure_ascii=False, default=str)

    if nom == "lire_contacts":
        type_contact = parametres.get("type_contact", "tous")
        data = db.lire_contacts(type_contact=type_contact)
        return json.dumps(data, ensure_ascii=False, default=str)

    if nom == "ajouter_contact":
        data = db.ajouter_contact(parametres)
        return json.dumps({"statut": "contact ajouté", "data": data}, ensure_ascii=False, default=str)

    if nom == "matcher_bien_acheteurs":
        data = db.matcher_bien_acheteurs(parametres["bien_id"])
        return json.dumps(data, ensure_ascii=False, default=str)

    if nom == "matcher_acheteur_biens":
        data = db.matcher_acheteur_biens(parametres["acheteur_id"])
        return json.dumps(data, ensure_ascii=False, default=str)

    if nom == "lire_mandats":
        statut = parametres.get("statut", "actif")
        data = db.lire_mandats(statut=statut)
        return json.dumps(data, ensure_ascii=False, default=str)

    if nom == "ajouter_visite":
        data = db.ajouter_visite(parametres)
        return json.dumps({"statut": "visite enregistrée", "data": data}, ensure_ascii=False, default=str)

    return json.dumps({"erreur": f"Outil inconnu : {nom}"})
