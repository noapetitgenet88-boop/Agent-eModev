"""
Connexion à Supabase et opérations sur la base de données.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client = None

def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


# ─── BIENS ────────────────────────────────────────────────────────────────────

def lire_biens(statut: str = "actif") -> list:
    db = get_client()
    q = db.table("biens").select("*")
    if statut != "tous":
        q = q.eq("statut", statut)
    return q.order("created_at", desc=True).execute().data


def chercher_biens(ville: str = "", prix_max: int = 0, surface_min: int = 0,
                   nb_pieces_min: int = 0, type_bien: str = "") -> list:
    db = get_client()
    q = db.table("biens").select("*").eq("statut", "actif")
    if ville:
        q = q.ilike("ville", f"%{ville}%")
    if prix_max:
        q = q.lte("prix", prix_max)
    if surface_min:
        q = q.gte("surface", surface_min)
    if nb_pieces_min:
        q = q.gte("nb_pieces", nb_pieces_min)
    if type_bien:
        q = q.ilike("type_bien", f"%{type_bien}%")
    return q.execute().data


def ajouter_bien(data: dict) -> dict:
    db = get_client()
    return db.table("biens").insert(data).execute().data


def modifier_bien(reference: str, data: dict) -> dict:
    db = get_client()
    return db.table("biens").update(data).eq("reference", reference).execute().data


# ─── CONTACTS ─────────────────────────────────────────────────────────────────

def lire_contacts(type_contact: str = "tous") -> list:
    db = get_client()
    q = db.table("contacts").select("*").eq("statut", "actif")
    if type_contact != "tous":
        q = q.eq("type_contact", type_contact)
    return q.order("created_at", desc=True).execute().data


def ajouter_contact(data: dict) -> dict:
    db = get_client()
    return db.table("contacts").insert(data).execute().data


def modifier_contact(id: int, data: dict) -> dict:
    db = get_client()
    return db.table("contacts").update(data).eq("id", id).execute().data


# ─── MANDATS ──────────────────────────────────────────────────────────────────

def lire_mandats(statut: str = "actif") -> list:
    db = get_client()
    q = db.table("mandats").select("*, biens(*), contacts(*)")
    if statut != "tous":
        q = q.eq("statut", statut)
    return q.order("created_at", desc=True).execute().data


def ajouter_mandat(data: dict) -> dict:
    db = get_client()
    return db.table("mandats").insert(data).execute().data


# ─── VISITES ──────────────────────────────────────────────────────────────────

def lire_visites(bien_id: int = None) -> list:
    db = get_client()
    q = db.table("visites").select("*, biens(*), contacts(*)")
    if bien_id:
        q = q.eq("bien_id", bien_id)
    return q.order("date_visite", desc=True).execute().data


def ajouter_visite(data: dict) -> dict:
    db = get_client()
    return db.table("visites").insert(data).execute().data


# ─── MATCHING acheteurs ↔ biens ───────────────────────────────────────────────

def matcher_acheteur_biens(acheteur_id: int) -> list:
    """Trouve les biens actifs qui correspondent aux critères d'un acheteur."""
    db = get_client()
    acheteur = db.table("contacts").select("*").eq("id", acheteur_id).execute().data
    if not acheteur:
        return []
    a = acheteur[0]

    q = db.table("biens").select("*").eq("statut", "actif")
    if a.get("budget_max"):
        q = q.lte("prix", a["budget_max"])
    if a.get("surface_min"):
        q = q.gte("surface", a["surface_min"])
    if a.get("nb_pieces_min"):
        q = q.gte("nb_pieces", a["nb_pieces_min"])
    if a.get("villes_recherchees"):
        villes = [v.strip() for v in a["villes_recherchees"].split(",")]
        # Cherche dans la première ville (Supabase ne supporte pas OR natif simplement)
        if villes:
            q = q.ilike("ville", f"%{villes[0]}%")

    return q.execute().data


def matcher_bien_acheteurs(bien_id: int) -> list:
    """Trouve les acheteurs dont les critères correspondent à un bien donné."""
    db = get_client()
    bien = db.table("biens").select("*").eq("id", bien_id).execute().data
    if not bien:
        return []
    b = bien[0]

    acheteurs = db.table("contacts").select("*").eq("type_contact", "acheteur").eq("statut", "actif").execute().data

    correspondances = []
    for a in acheteurs:
        score = 0
        if a.get("budget_max") and b.get("prix") and b["prix"] <= a["budget_max"]:
            score += 3
        if a.get("surface_min") and b.get("surface") and b["surface"] >= a["surface_min"]:
            score += 2
        if a.get("nb_pieces_min") and b.get("nb_pieces") and b["nb_pieces"] >= a["nb_pieces_min"]:
            score += 2
        if a.get("villes_recherchees") and b.get("ville"):
            if b["ville"].lower() in a["villes_recherchees"].lower():
                score += 3
        if score >= 3:
            correspondances.append({**a, "score_matching": score})

    return sorted(correspondances, key=lambda x: x["score_matching"], reverse=True)
