# app.py — Point d'entrée principal
import streamlit as st
from authentification import (connecter_utilisateur, deconnecter,
                                    inscrire_eleve, envoyer_reset_email,
                                    changer_mot_de_passe, est_connecte)
from securite import role_actuel

st.set_page_config(
    page_title="Plateforme d'apprentissage",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1a1a2e; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    .stButton > button[kind="primary"] {
        background-color: #1a1a2e;
        color: white;
        border-radius: 8px;
        width: 100%;
    }
    div[data-testid="metric-container"] {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #e0e0e0;
    }
    .stTextInput input { font-size: 15px; }
    .stSelectbox select { font-size: 15px; }
</style>
""", unsafe_allow_html=True)

# ── Initialisation session ─────────────────────────────────────────
if "utilisateur" not in st.session_state:
    st.session_state.utilisateur = None
if "page_auth" not in st.session_state:
    st.session_state.page_auth = "connexion"


# ── Sidebar ────────────────────────────────────────────────────────
def afficher_sidebar():
    with st.sidebar:
        st.markdown("## 🎓 Plateforme\nd'apprentissage")
        st.divider()

        if est_connecte():
            u = st.session_state.utilisateur
            icones = {"super_admin": "👑", "admin": "🛡️", "professeur": "👨‍🏫", "eleve": "🎓"}
            icone  = icones.get(u.get("role"), "👤")
            st.markdown(f"**{icone} {u.get('prenom')} {u.get('nom')}**")
            st.caption(f"Rôle : {u.get('role','—')}")
            st.divider()

            # Changer mot de passe
            with st.expander("🔑 Changer mon mot de passe"):
                nouveau_mdp = st.text_input("Nouveau mot de passe", type="password",
                                             key="new_mdp")
                confirmer   = st.text_input("Confirmer", type="password",
                                             key="confirm_mdp")
                if st.button("Changer", key="btn_change_mdp"):
                    if not nouveau_mdp or not confirmer:
                        st.warning("Remplissez les deux champs.")
                    elif nouveau_mdp != confirmer:
                        st.error("Les mots de passe ne correspondent pas.")
                    elif len(nouveau_mdp) < 6:
                        st.error("Minimum 6 caractères.")
                    else:
                        ok, msg = changer_mot_de_passe(u["uid"], nouveau_mdp)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)

            if st.button("🚪 Se déconnecter", use_container_width=True):
                deconnecter()
                st.rerun()
        else:
            st.caption("Connectez-vous pour accéder à la plateforme.")


# ── Page Connexion ─────────────────────────────────────────────────
def page_connexion():
    col_g, col_c, col_d = st.columns([1, 2, 1])
    with col_c:
        st.markdown("## 🎓 Bienvenue sur la plateforme")
        st.markdown("Connectez-vous pour accéder à votre espace.")
        st.divider()

        email = st.text_input("📧 Email", placeholder="votre@email.com")
        mdp   = st.text_input("🔒 Mot de passe", type="password")

        if st.button("Se connecter", type="primary", use_container_width=True):
            if not email or not mdp:
                st.warning("⚠️ Remplissez tous les champs.")
            else:
                with st.spinner("Connexion..."):
                    profil = connecter_utilisateur(email, mdp)
                if profil:
                    st.session_state.utilisateur = profil
                    st.rerun()
                else:
                    st.error("❌ Email ou mot de passe incorrect.")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Créer un compte élève", use_container_width=True):
                st.session_state.page_auth = "inscription"
                st.rerun()
        with col2:
            if st.button("🔑 Mot de passe oublié", use_container_width=True):
                st.session_state.page_auth = "reset"
                st.rerun()


# ── Page Inscription élève ─────────────────────────────────────────
def page_inscription():
    col_g, col_c, col_d = st.columns([1, 2, 1])
    with col_c:
        st.markdown("## ✏️ Créer un compte élève")
        st.caption("Vous avez besoin du code donné par votre professeur.")
        st.divider()

        CLASSES = ["6e", "5e", "4e", "1ère", "Tle"]

        col1, col2 = st.columns(2)
        with col1:
            prenom = st.text_input("Prénom")
            email  = st.text_input("Email")
            classe = st.selectbox("Votre classe", CLASSES)
        with col2:
            nom       = st.text_input("Nom")
            telephone = st.text_input("Téléphone", placeholder="+237600000000",
                                       help="Pour récupérer votre mot de passe en cas d'oubli")
            code      = st.text_input("🔑 Code de votre professeur",
                                       placeholder="Ex: A3F7B2C1")

        mdp      = st.text_input("Mot de passe", type="password",
                                  help="Minimum 6 caractères")
        confirmer = st.text_input("Confirmer le mot de passe", type="password")

        if st.button("✅ Créer mon compte", type="primary", use_container_width=True):
            if not all([prenom, nom, email, mdp, code]):
                st.warning("⚠️ Remplissez tous les champs obligatoires.")
            elif mdp != confirmer:
                st.error("❌ Les mots de passe ne correspondent pas.")
            elif len(mdp) < 6:
                st.error("❌ Le mot de passe doit avoir au moins 6 caractères.")
            else:
                with st.spinner("Création du compte..."):
                    ok, msg = inscrire_eleve(prenom, nom, email, mdp,
                                             telephone, classe, code.strip().upper())
                if ok:
                    st.success(f"✅ {msg} Connectez-vous maintenant.")
                    st.session_state.page_auth = "connexion"
                    st.rerun()
                else:
                    st.error(msg)

        if st.button("← Retour à la connexion", use_container_width=True):
            st.session_state.page_auth = "connexion"
            st.rerun()


# ── Page Mot de passe oublié ───────────────────────────────────────
def page_reset():
    col_g, col_c, col_d = st.columns([1, 2, 1])
    with col_c:
        st.markdown("## 🔑 Mot de passe oublié")
        st.caption("Entrez votre email — nous vous enverrons un lien de réinitialisation.")
        st.divider()

        email = st.text_input("📧 Votre email")

        if st.button("📧 Envoyer le lien", type="primary", use_container_width=True):
            if not email:
                st.warning("⚠️ Entrez votre email.")
            else:
                with st.spinner("Envoi en cours..."):
                    ok, msg = envoyer_reset_email(email)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        if st.button("← Retour à la connexion", use_container_width=True):
            st.session_state.page_auth = "connexion"
            st.rerun()


# ── Routeur principal ──────────────────────────────────────────────
def main():
    afficher_sidebar()

    if not est_connecte():
        if st.session_state.page_auth == "inscription":
            page_inscription()
        elif st.session_state.page_auth == "reset":
            page_reset()
        else:
            page_connexion()
        return

    role = role_actuel()

    if role == "super_admin":
        from vue_superadmin import afficher_vue_superadmin
        afficher_vue_superadmin()
    elif role == "admin":
        from vue_admin import afficher_vue_admin
        afficher_vue_admin()
    elif role == "professeur":
        from vue_professeur import afficher_vue_professeur
        afficher_vue_professeur()
    elif role == "eleve":
        from vue_eleve import afficher_vue_eleve
        afficher_vue_eleve()
    else:
        st.error("Rôle inconnu.")
        if st.button("Se déconnecter"):
            deconnecter()
            st.rerun()


if __name__ == "__main__":
    main()
