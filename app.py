"""
Interface web de l'agent immobilier — Raphaël Petitgenet / eModev
Lancement : streamlit run app.py
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import anthropic
from dotenv import load_dotenv

from outils import TOOLS, executer_outil
from parametres import charger, sauvegarder, construire_system_prompt
from memoire import construire_contexte_memoire, ajouter_note

load_dotenv()

# Sur Streamlit Cloud, la clé est dans st.secrets (pas dans .env)
if not os.getenv("ANTHROPIC_API_KEY") and hasattr(st, "secrets"):
    try:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass

# ─── Configuration de la page ─────────────────────────────────────────────────

st.set_page_config(
    page_title="Agent Immobilier — eModev",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background-color: #0f1117; }
section[data-testid="stSidebar"] {
    background-color: #161b27;
    border-right: 1px solid #2a2f3e;
}
.stChatMessage[data-testid="stChatMessageAssistant"] {
    background-color: #141920;
    border-left: 3px solid #3b82f6;
    border-radius: 10px;
    padding: 4px 8px;
}
.stChatMessage[data-testid="stChatMessageUser"] {
    background-color: #1e2535;
    border-radius: 10px;
    padding: 4px 8px;
}
h1 { color: #f0f4ff !important; font-size: 1.4rem !important; }
.section-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: #6b7280;
    margin: 14px 0 6px 0;
}
.doc-puce { font-size: 11px; color: #10b981; margin: 2px 0; }
</style>
""", unsafe_allow_html=True)


# ─── État de la session ────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "docs_session" not in st.session_state:
    st.session_state.docs_session = []
if "settings" not in st.session_state:
    st.session_state.settings = charger()
if "page" not in st.session_state:
    st.session_state.page = "chat"


# ─── Sidebar ──────────────────────────────────────────────────────────────────

settings = st.session_state.settings
profil = settings["profil"]

with st.sidebar:
    st.markdown(f"## 🏠 {profil['reseau']}")
    st.markdown(f"**Agent immobilier IA**")
    st.markdown(f"{profil['nom']} · {profil['zone'].split('/')[0].strip()}")
    st.divider()

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 Chat", use_container_width=True,
                     type="primary" if st.session_state.page == "chat" else "secondary"):
            st.session_state.page = "chat"
            st.rerun()
    with col2:
        if st.button("⚙️ Réglages", use_container_width=True,
                     type="primary" if st.session_state.page == "settings" else "secondary"):
            st.session_state.page = "settings"
            st.rerun()

    st.divider()

    if st.session_state.page == "chat":
        st.markdown('<div class="section-label">Raccourcis</div>', unsafe_allow_html=True)
        for i, rc in enumerate(settings["raccourcis"]):
            if st.button(rc["label"], key=f"rc_{i}", use_container_width=True):
                st.session_state["prefill"] = rc["texte"]

        if settings.get("templates"):
            st.markdown('<div class="section-label">Mes templates</div>', unsafe_allow_html=True)
            for i, t in enumerate(settings["templates"]):
                if st.button(f"📄 {t['nom']}", key=f"tpl_{i}", use_container_width=True):
                    st.session_state["prefill"] = t["contenu"]

        st.divider()
        st.markdown('<div class="section-label">Documents produits</div>', unsafe_allow_html=True)
        if st.session_state.docs_session:
            for chemin in reversed(st.session_state.docs_session[-6:]):
                nom = Path(chemin).name.replace("_", " ").replace(".txt", "")
                st.markdown(f'<div class="doc-puce">✓ {nom[:38]}</div>', unsafe_allow_html=True)
        else:
            st.caption("Aucun document produit")

        st.divider()
        if st.button("🔄 Nouvelle conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.docs_session = []
            st.rerun()

    cle_ok = os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-ant-")
    st.markdown(
        f'<div style="margin-top:8px;font-size:11px;color:{"#10b981" if cle_ok else "#ef4444"}">'
        f'{"● API connectée" if cle_ok else "● Clé API manquante"}</div>',
        unsafe_allow_html=True
    )


# ─── PAGE RÉGLAGES ─────────────────────────────────────────────────────────────

if st.session_state.page == "settings":
    st.markdown("## ⚙️ Réglages")

    tab1, tab2, tab3, tab4 = st.tabs(["👤 Mon profil", "⚡ Raccourcis", "📄 Templates", "🧠 Mémoire"])

    # ── Onglet Profil ──────────────────────────────────────────────────────────
    with tab1:
        st.markdown("#### Informations personnelles")
        st.caption("Ces informations sont utilisées dans tous les documents produits par l'agent.")

        p = settings["profil"]
        col1, col2 = st.columns(2)
        with col1:
            p["nom"]      = st.text_input("Nom complet", value=p["nom"])
            p["reseau"]   = st.text_input("Réseau / Enseigne", value=p["reseau"])
            p["email"]    = st.text_input("Email professionnel", value=p.get("email", ""))
            p["logiciel"] = st.text_input("Logiciel d'agence", value=p.get("logiciel", "Netty"))
        with col2:
            p["statut"]   = st.text_input("Statut professionnel", value=p["statut"])
            p["zone"]     = st.text_input("Zone d'activité", value=p["zone"])
            p["telephone"]= st.text_input("Téléphone", value=p.get("telephone", ""))
            p["site"]     = st.text_input("Site web", value=p.get("site", ""))

        p["marche"] = st.text_area("Types de biens / marché", value=p.get("marche", ""), height=80)

        if st.button("💾 Sauvegarder le profil", type="primary"):
            settings["profil"] = p
            sauvegarder(settings)
            st.session_state.settings = settings
            st.success("Profil sauvegardé — l'agent utilise maintenant tes nouvelles informations.")

    # ── Onglet Raccourcis ──────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Mes raccourcis")
        st.caption("Modifie, ajoute ou supprime les boutons qui apparaissent dans le menu de gauche.")

        raccourcis = settings["raccourcis"]
        a_supprimer = []

        for i, rc in enumerate(raccourcis):
            with st.expander(rc["label"], expanded=False):
                col1, col2 = st.columns([1, 3])
                with col1:
                    raccourcis[i]["label"] = st.text_input("Bouton", value=rc["label"], key=f"rl_{i}")
                with col2:
                    raccourcis[i]["texte"] = st.text_input("Texte envoyé", value=rc["texte"], key=f"rt_{i}")
                if st.button("🗑️ Supprimer", key=f"rd_{i}"):
                    a_supprimer.append(i)

        for i in reversed(a_supprimer):
            raccourcis.pop(i)

        st.divider()
        st.markdown("**Ajouter un raccourci**")
        col1, col2 = st.columns([1, 3])
        with col1:
            new_label = st.text_input("Nom du bouton", placeholder="📝 Mon raccourci", key="new_label")
        with col2:
            new_texte = st.text_input("Texte à envoyer", placeholder="Rédige un...", key="new_texte")

        if st.button("➕ Ajouter", type="primary"):
            if new_label and new_texte:
                raccourcis.append({"label": new_label, "texte": new_texte})
                settings["raccourcis"] = raccourcis
                sauvegarder(settings)
                st.session_state.settings = settings
                st.success("Raccourci ajouté !")
                st.rerun()
            else:
                st.warning("Remplis les deux champs.")

        if st.button("💾 Sauvegarder les raccourcis", type="secondary"):
            settings["raccourcis"] = raccourcis
            sauvegarder(settings)
            st.session_state.settings = settings
            st.success("Raccourcis sauvegardés.")

    # ── Onglet Templates ───────────────────────────────────────────────────────
    with tab3:
        st.markdown("#### Mes templates")
        st.caption("Sauvegarde tes formulations préférées pour les réutiliser en un clic.")

        templates = settings.get("templates", [])
        a_supprimer_t = []

        for i, t in enumerate(templates):
            with st.expander(t["nom"], expanded=False):
                templates[i]["nom"]     = st.text_input("Nom", value=t["nom"], key=f"tn_{i}")
                templates[i]["contenu"] = st.text_area("Contenu", value=t["contenu"], key=f"tc_{i}", height=100)
                if st.button("🗑️ Supprimer", key=f"td_{i}"):
                    a_supprimer_t.append(i)

        for i in reversed(a_supprimer_t):
            templates.pop(i)

        st.divider()
        st.markdown("**Nouveau template**")
        new_tnom    = st.text_input("Nom du template", placeholder="Ex : Mail offre basse", key="new_tnom")
        new_tcontenu = st.text_area("Contenu", placeholder="Rédige un mail pour...", key="new_tcontenu", height=100)

        if st.button("➕ Ajouter le template", type="primary"):
            if new_tnom and new_tcontenu:
                templates.append({"nom": new_tnom, "contenu": new_tcontenu})
                settings["templates"] = templates
                sauvegarder(settings)
                st.session_state.settings = settings
                st.success("Template ajouté !")
                st.rerun()
            else:
                st.warning("Remplis les deux champs.")

        if templates and st.button("💾 Sauvegarder les templates", type="secondary"):
            settings["templates"] = templates
            sauvegarder(settings)
            st.session_state.settings = settings
            st.success("Templates sauvegardés.")

    # ── Onglet Mémoire ─────────────────────────────────────────────────────────
    with tab4:
        from memoire import charger as charger_mem, sauvegarder as sauvegarder_mem, ajouter_note
        import memoire as mem_module

        st.markdown("#### Mémoire de l'agent")
        st.caption("L'agent se souvient de ces informations dans toutes tes sessions.")

        mem = charger_mem()

        # Notes libres
        st.markdown("**Notes & informations marché**")
        nouvelle_note = st.text_input("Ajouter une note", placeholder="Ex : Prix moyen secteur Charmes : 1100€/m²")
        if st.button("➕ Ajouter la note") and nouvelle_note:
            ajouter_note(nouvelle_note)
            st.success("Note ajoutée !")
            st.rerun()

        if mem.get("notes"):
            for i, n in enumerate(reversed(mem["notes"][-10:])):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"`{n['date']}` {n['contenu']}")
                with col2:
                    if st.button("🗑️", key=f"del_note_{i}"):
                        idx = len(mem["notes"]) - 1 - i
                        mem["notes"].pop(idx)
                        sauvegarder_mem(mem)
                        st.rerun()

        st.divider()

        # Biens en portefeuille
        st.markdown("**Biens en portefeuille**")
        with st.expander("Ajouter un bien"):
            c1, c2, c3 = st.columns(3)
            b_ref   = c1.text_input("Référence", placeholder="M2025-001", key="b_ref")
            b_type  = c2.text_input("Type", placeholder="Maison 4p", key="b_type")
            b_ville = c3.text_input("Ville", placeholder="Épinal", key="b_ville")
            c4, c5 = st.columns(2)
            b_surf  = c4.text_input("Surface (m²)", key="b_surf")
            b_prix  = c5.text_input("Prix (€)", key="b_prix")
            b_stat  = st.selectbox("Statut", ["actif", "compromis", "vendu", "suspendu"], key="b_stat")
            if st.button("➕ Ajouter ce bien"):
                if b_ref and b_ville:
                    mem["biens"].append({"ref": b_ref, "type": b_type, "ville": b_ville,
                                         "surface": b_surf, "prix": b_prix, "statut": b_stat})
                    sauvegarder_mem(mem)
                    st.success("Bien ajouté à la mémoire !")
                    st.rerun()

        if mem.get("biens"):
            for b in mem["biens"]:
                st.markdown(f"- **{b.get('ref')}** — {b.get('type')} {b.get('surface')}m² | {b.get('ville')} | {b.get('prix')}€ | _{b.get('statut')}_")

        st.divider()

        # Clients
        st.markdown("**Clients suivis**")
        with st.expander("Ajouter un client"):
            cl_nom    = st.text_input("Nom", key="cl_nom")
            cl_type   = st.selectbox("Type", ["acheteur", "vendeur"], key="cl_type")
            cl_budget = st.text_input("Budget (€)", key="cl_budget")
            cl_sect   = st.text_input("Secteur recherché", key="cl_sect")
            cl_stat   = st.text_input("Statut", placeholder="En recherche active", key="cl_stat")
            if st.button("➕ Ajouter ce client"):
                if cl_nom:
                    mem["clients"].append({"nom": cl_nom, "type": cl_type,
                                           "budget": cl_budget, "secteur": cl_sect, "statut": cl_stat})
                    sauvegarder_mem(mem)
                    st.success("Client ajouté !")
                    st.rerun()

        if mem.get("clients"):
            for c in mem["clients"]:
                st.markdown(f"- **{c.get('nom')}** ({c.get('type')}) — Budget : {c.get('budget')}€ | {c.get('secteur')} | _{c.get('statut')}_")

    st.stop()


# ─── PAGE CHAT ─────────────────────────────────────────────────────────────────

col_titre, col_date = st.columns([3, 1])
with col_titre:
    st.markdown(f"## Agent Immobilier {profil['reseau']}")
with col_date:
    st.markdown(f'<p style="color:#6b7280;text-align:right;margin-top:8px">{datetime.now():%-d %B %Y}</p>',
                unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown(f"""
    <div style="color:#6b7280;font-size:0.9rem;margin:24px 0 8px 0">
    Bonjour {profil['nom'].split()[0]} ! Je suis ton copilote immobilier.<br>
    Utilise les <strong>raccourcis</strong> à gauche ou tape directement ta demande.
    </div>
    """, unsafe_allow_html=True)

for msg in st.session_state.messages:
    role = msg["role"]
    with st.chat_message(role, avatar="👤" if role == "user" else "🏠"):
        contenu = msg["content"]
        if isinstance(contenu, str):
            st.markdown(contenu)
            if role == "assistant":
                st.button("📋 Copier", key=f"copy_{hash(contenu)}",
                          on_click=lambda t=contenu: st.write(
                              f'<script>navigator.clipboard.writeText({json.dumps(t)})</script>',
                              unsafe_allow_html=True))
        elif isinstance(contenu, list):
            for bloc in contenu:
                if hasattr(bloc, "type") and bloc.type == "text" and bloc.text:
                    st.markdown(bloc.text)


# ─── Boucle agentique ─────────────────────────────────────────────────────────

def _messages_api() -> list:
    """Construit la liste de messages pour l'API en filtrant les blocs thinking."""
    out = []
    for m in st.session_state.messages:
        if m["role"] not in ("user", "assistant"):
            continue
        contenu = m["content"]
        if isinstance(contenu, list):
            contenu = [b for b in contenu
                       if not (hasattr(b, "type") and b.type == "thinking")]
        out.append({"role": m["role"], "content": contenu})
    return out


def executer_agent(saisie: str, placeholder) -> str:
    """Boucle agentique avec streaming — affiche le texte mot par mot."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    contexte_mem = construire_contexte_memoire()
    system_prompt = construire_system_prompt(st.session_state.settings, contexte_mem)

    def _appeler_avec_streaming(messages: list) -> tuple[str, list]:
        """Appelle l'API en streaming, retourne (texte_final, content_blocks)."""
        texte_accumule = ""
        content_blocks = []

        for tentative in range(1, 4):
            try:
                with client.messages.stream(
                    model="claude-opus-4-8",
                    max_tokens=4096,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=messages,
                    thinking={"type": "adaptive"},
                ) as stream:
                    for event in stream:
                        # Streaming du texte mot par mot
                        if hasattr(event, "type"):
                            if event.type == "content_block_delta":
                                delta = getattr(event, "delta", None)
                                if delta and hasattr(delta, "type") and delta.type == "text_delta":
                                    texte_accumule += delta.text
                                    placeholder.markdown(texte_accumule + "▌")

                    final = stream.get_final_message()
                    content_blocks = final.content
                    return texte_accumule, content_blocks, final.stop_reason

            except anthropic.RateLimitError:
                if tentative < 3:
                    placeholder.markdown("_Limite de requêtes — nouvelle tentative dans 10s..._")
                    time.sleep(10)
                    continue
                st.error("Limite de requêtes atteinte.")
                return "", [], "error"
            except anthropic.AuthenticationError:
                st.error("Clé API invalide. Vérifie le fichier .env.")
                return "", [], "error"
            except Exception as e:
                if tentative < 3:
                    time.sleep(3)
                    continue
                st.error(f"Erreur : {e}")
                return "", [], "error"

        return "", [], "error"

    # Premier appel
    messages = _messages_api()
    texte, content_blocks, stop_reason = _appeler_avec_streaming(messages)

    if stop_reason == "error":
        return None

    st.session_state.messages.append({"role": "assistant", "content": content_blocks})

    if stop_reason == "end_turn":
        placeholder.markdown(texte)
        return texte

    # Appel avec outils
    if stop_reason == "tool_use":
        resultats = []
        for bloc in content_blocks:
            if hasattr(bloc, "type") and bloc.type == "tool_use":
                placeholder.markdown(f"_⟳ {bloc.name.replace('_', ' ')}..._")
                resultat = executer_outil(bloc.name, bloc.input)
                if bloc.name == "sauvegarder_document":
                    try:
                        data = json.loads(resultat)
                        if "chemin" in data:
                            st.session_state.docs_session.append(data["chemin"])
                    except Exception:
                        pass
                resultats.append({"type": "tool_result", "tool_use_id": bloc.id, "content": resultat})

        st.session_state.messages.append({"role": "user", "content": resultats})
        placeholder.markdown("_Traitement..._")

        texte2, content2, _ = _appeler_avec_streaming(_messages_api())
        st.session_state.messages.append({"role": "assistant", "content": content2})
        placeholder.markdown(texte2)
        return texte2

    placeholder.markdown(texte)
    return texte


def _texte(content) -> str:
    if isinstance(content, list):
        return "\n".join(
            b.text for b in content
            if hasattr(b, "type") and b.type == "text" and b.text
        ).strip()
    return str(content)


# ─── Saisie ───────────────────────────────────────────────────────────────────

valeur_prefill = st.session_state.pop("prefill", "")
if valeur_prefill:
    st.info(f"💡 Raccourci sélectionné — complète et envoie :\n\n`{valeur_prefill}`")

saisie = st.chat_input("Pose une question ou donne une tâche...")

if saisie:
    if not os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-ant-"):
        st.error("Clé API manquante. Renseigne ANTHROPIC_API_KEY dans le fichier .env puis relance.")
        st.stop()

    with st.chat_message("user", avatar="👤"):
        st.markdown(saisie)
    st.session_state.messages.append({"role": "user", "content": saisie})

    with st.chat_message("assistant", avatar="🏠"):
        placeholder = st.empty()
        reponse = executer_agent(saisie, placeholder)
        if reponse:
            if st.button("📋 Copier la réponse", key=f"copy_last"):
                st.toast("Copié !", icon="✅")
