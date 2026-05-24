# vues/vue_superadmin.py — Espace Super Administrateur
import streamlit as st
from authentification import creer_compte, supprimer_compte
from utilisateur import SuperAdmin
from securite import exiger_role


def afficher_vue_superadmin():
    exiger_role(["super_admin"])
    utilisateur = st.session_state.utilisateur

    st.title("👑 Espace Super Administrateur")
    st.caption(f"Connecté : {utilisateur['prenom']} {utilisateur['nom']}")

    onglet1, onglet2, onglet3 = st.tabs([
        "👥 Utilisateurs",
        "➕ Créer un compte",
        "📊 Vue globale",
    ])

    with onglet1:
        _onglet_utilisateurs()
    with onglet2:
        _onglet_creation()
    with onglet3:
        _onglet_vue_globale()


def _onglet_utilisateurs():
    st.subheader("👥 Tous les utilisateurs")
    tous = SuperAdmin.get_tous_utilisateurs()

    filtre = st.selectbox("Filtrer", ["Tous", "super_admin", "admin", "professeur", "eleve"])
    if filtre != "Tous":
        tous = [u for u in tous if u.get("role") == filtre]

    if not tous:
        st.info("Aucun utilisateur trouvé.")
        return

    st.markdown(f"**{len(tous)} utilisateur(s)**")

    for u in sorted(tous, key=lambda x: x.get("role", "")):
        icones = {"super_admin": "👑", "admin": "🛡️", "professeur": "👨‍🏫", "eleve": "🎓"}
        icone  = icones.get(u.get("role"), "👤")
        en_ligne = "🟢" if u.get("en_ligne") else "⚫"

        with st.expander(f"{icone} {en_ligne} {u.get('nom','?')} {u.get('prenom','?')} — {u.get('role','?')}"):
            col1, col2 = st.columns(2)
            col1.markdown(f"**Email :** {u.get('email','—')}")
            col2.markdown(f"**Tél :** {u.get('telephone','—')}")
            col1.markdown(f"**Inscrit le :** {u.get('date_creation','—')[:10]}")

            if u.get("role") == "professeur":
                st.markdown(f"**Matières :** {', '.join(u.get('matieres',[]))}")
                st.markdown(f"**Code invitation :** `{u.get('code_invitation','—')}`")
            if u.get("role") == "eleve":
                st.markdown(f"**Classe :** {u.get('classe','—')}")

            uid_actuel = st.session_state.utilisateur["uid"]
            if u["id"] != uid_actuel and u.get("role") != "super_admin":
                if st.button(f"🗑️ Supprimer", key=f"del_{u['id']}"):
                    ok, msg = supprimer_compte(u["id"])
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


def _onglet_creation():
    st.subheader("➕ Créer un nouveau compte")

    role = st.selectbox("Rôle", ["professeur", "admin"])

    col1, col2 = st.columns(2)
    with col1:
        prenom = st.text_input("Prénom")
        email  = st.text_input("Email")
    with col2:
        nom       = st.text_input("Nom")
        telephone = st.text_input("Téléphone", placeholder="+237600000000")

    mdp = st.text_input("Mot de passe temporaire", type="password")

    matieres = []
    if role == "professeur":
        matieres_input = st.text_input("Matières (séparées par des virgules)",
                                        placeholder="Français, Mathématiques")
        matieres = [m.strip() for m in matieres_input.split(",") if m.strip()]

    if st.button("✅ Créer le compte", type="primary"):
        if not all([prenom, nom, email, mdp]):
            st.warning("⚠️ Remplissez tous les champs.")
            return
        ok, msg = creer_compte(prenom, nom, email, mdp, telephone, role, matieres)
        if ok:
            st.success(f"✅ Compte {role} créé pour {nom} {prenom}.")
            if role == "professeur":
                st.info("Le code d'invitation est visible dans la liste des utilisateurs.")
        else:
            st.error(msg)


def _onglet_vue_globale():
    st.subheader("📊 Statistiques globales")
    tous = SuperAdmin.get_tous_utilisateurs()

    admins = [u for u in tous if u.get("role") == "admin"]
    profs  = [u for u in tous if u.get("role") == "professeur"]
    eleves = [u for u in tous if u.get("role") == "eleve"]
    en_ligne = [u for u in tous if u.get("en_ligne")]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🛡️ Admins",       len(admins))
    col2.metric("👨‍🏫 Professeurs", len(profs))
    col3.metric("🎓 Élèves",       len(eleves))
    col4.metric("🟢 En ligne",     len(en_ligne))

    if eleves:
        st.divider()
        st.markdown("**Répartition par classe :**")
        classes = {}
        for e in eleves:
            c = e.get("classe", "—")
            classes[c] = classes.get(c, 0) + 1
        for classe, nb in sorted(classes.items()):
            st.markdown(f"- **{classe}** : {nb} élève(s)")
