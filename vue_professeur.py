# vues/vue_professeur.py — Espace professeur (version corrigée)
import streamlit as st
import datetime
import uuid
from config import get_db, get_bucket
from travail import Travail, ExerciceQCM
from utilisateur import Professeur
from securite import exiger_role, verifier_acces_professeur, bloquer_acces_non_autorise


def afficher_vue_professeur():
    exiger_role(["professeur", "admin", "super_admin"])
    utilisateur = st.session_state.utilisateur
    prof_id     = utilisateur["uid"]

    if not verifier_acces_professeur(prof_id):
        bloquer_acces_non_autorise()

    # ── Tableau de bord ──
    st.title(f"👨‍🏫 Bonjour, {utilisateur['prenom']} {utilisateur['nom']} !")

    # Statistiques rapides
    nb_eleves   = Professeur.get_nb_eleves(prof_id)
    travaux     = Professeur.get_travaux_a_corriger(prof_id)
    a_corriger  = len([t for t in travaux if t.get("statut") == "soumis"])
    corriges    = len([t for t in travaux if t.get("statut") == "corrigé"])
    publies     = len([t for t in travaux if t.get("statut") == "publié"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Mes élèves",       nb_eleves)
    col2.metric("📥 À corriger",        a_corriger)
    col3.metric("✏️ Corrigés",          corriges)
    col4.metric("✅ Publiés",           publies)

    # Code d'invitation
    code = utilisateur.get("code_invitation", "—")
    st.info(f"🔑 Code d'invitation pour vos élèves : **{code}** — Donnez ce code à vos élèves pour qu'ils s'inscrivent.")

    st.divider()

    # ── Onglets ──
    onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
        "📂 Publier des exercices",
        "📥 Boîte de réception",
        "✏️ Corriger",
        "✅ Publier corrections",
        "👥 Mes élèves",
    ])

    with onglet1:
        _onglet_exercices(utilisateur)
    with onglet2:
        _onglet_reception(utilisateur)
    with onglet3:
        _onglet_correction(utilisateur)
    with onglet4:
        _onglet_publication(utilisateur)
    with onglet5:
        _onglet_eleves(utilisateur)


# ── ONGLET 1 : Publier des exercices ──────────────────────────────
def _onglet_exercices(utilisateur: dict):
    st.subheader("📂 Publier un exercice pour vos élèves")
    st.caption("Vos élèves verront cet exercice dans leur espace.")

    prof_id  = utilisateur["uid"]
    matieres = utilisateur.get("matieres", [])
    classes  = ["6e", "5e", "4e", "1ère", "Tle"]

    # Informations de l'exercice
    col1, col2 = st.columns(2)
    with col1:
        classe = st.selectbox("🎓 Classe concernée", classes)
    with col2:
        if matieres:
            matiere = st.selectbox("📚 Matière", matieres)
        else:
            matiere = st.text_input("📚 Matière")

    titre      = st.text_input("📌 Titre de l'exercice", placeholder="Ex: Analyse de texte — La Fontaine")
    consignes  = st.text_area("📋 Consignes et explications",
                               placeholder="Expliquez ici ce que vous attendez de vos élèves, les détails, les critères d'évaluation...",
                               height=150)
    format_ex  = st.selectbox("📝 Format de travail",
                               ["Devoir individuel", "Travail de groupe", "QCM", "Rédaction", "Exposé"])
    date_limite = st.date_input("📅 Date limite de remise", min_value=datetime.date.today())

    st.divider()

    # Type de contenu
    type_contenu = st.radio("Type de contenu",
                             ["Rédiger l'exercice ici", "Uploader un fichier", "Les deux"],
                             horizontal=True)

    contenu_redige = ""
    fichier_url    = ""

    if type_contenu in ["Rédiger l'exercice ici", "Les deux"]:
        contenu_redige = st.text_area("✏️ Rédigez votre exercice",
                                       placeholder="Écrivez votre exercice ici...",
                                       height=200)

    if type_contenu in ["Uploader un fichier", "Les deux"]:
        fichier = st.file_uploader("📎 Fichier exercice", type=["pdf", "docx", "doc", "txt", "png", "jpg"])
        if fichier:
            try:
                bucket  = get_bucket()
                chemin  = f"exercices/{prof_id}/{classe}/{matiere}/{fichier.name}"
                blob    = bucket.blob(chemin)
                blob.upload_from_string(fichier.read(), content_type="application/octet-stream")
                blob.make_public()
                fichier_url = blob.public_url
                st.success(f"✅ Fichier prêt : {fichier.name}")
            except Exception as e:
                st.error(f"Erreur upload : {e}")

    if st.button("🚀 Publier l'exercice", type="primary"):
        if not titre or not consignes:
            st.warning("⚠️ Le titre et les consignes sont obligatoires.")
            return
        exercice = {
            "id":            str(uuid.uuid4()),
            "prof_id":       prof_id,
            "classe":        classe,
            "matiere":       matiere,
            "titre":         titre,
            "consignes":     consignes,
            "format":        format_ex,
            "date_limite":   str(date_limite),
            "contenu":       contenu_redige,
            "fichier_url":   fichier_url,
            "date_creation": datetime.datetime.now().isoformat(),
        }
        get_db().collection("exercices_publies").add(exercice)
        st.success(f"✅ Exercice publié ! Vos élèves de {classe} peuvent maintenant le voir.")
        st.balloons()


# ── ONGLET 2 : Boîte de réception ─────────────────────────────────
def _onglet_reception(utilisateur: dict):
    st.subheader("📥 Boîte de réception — Travaux soumis")
    st.caption("Tous les travaux soumis par vos élèves apparaissent ici.")

    prof_id = utilisateur["uid"]
    classes = ["Toutes"] + ["6e", "5e", "4e", "1ère", "Tle"]

    col1, col2 = st.columns(2)
    with col1:
        filtre_classe = st.selectbox("Filtrer par classe", classes, key="reception_classe")
    with col2:
        filtre_statut = st.selectbox("Filtrer par statut",
                                      ["Tous", "soumis", "corrigé", "publié"],
                                      key="reception_statut")

    classe_param = None if filtre_classe == "Toutes" else filtre_classe
    travaux      = Professeur.get_travaux_a_corriger(prof_id, classe=classe_param)

    if filtre_statut != "Tous":
        travaux = [t for t in travaux if t.get("statut") == filtre_statut]

    travaux = sorted(travaux, key=lambda t: t.get("date_soumis", ""), reverse=True)

    if not travaux:
        st.info("📭 Aucun travail reçu pour le moment.")
        return

    st.markdown(f"**{len(travaux)} travail(aux) reçu(s)**")

    for t in travaux:
        statut = t.get("statut", "soumis")
        icone  = {"soumis": "🆕", "corrigé": "🔒", "publié": "✅"}.get(statut, "🕐")
        label  = f"{icone} {t['eleve_nom']} | {t.get('classe','?')} | {t['matiere']} | {t.get('date_soumis','')[:10]}"

        with st.expander(label):
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"**Élève :** {t['eleve_nom']}")
            col2.markdown(f"**Classe :** {t.get('classe','?')}")
            col3.markdown(f"**Format :** {t.get('format_travail','?')}")

            st.markdown(f"**Matière :** {t['matiere']} — {t.get('discipline','')}")
            st.markdown(f"**Soumis le :** {t.get('date_soumis','')[:10]}")
            st.markdown(f"**Statut :** {statut}")

            if t.get("contenu_texte"):
                st.markdown("**Contenu :**")
                st.text_area("", value=t["contenu_texte"], height=150,
                             disabled=True, key=f"rec_txt_{t['id']}")
            if t.get("fichier_url"):
                st.markdown(f"[📎 Voir le fichier]({t['fichier_url']})")


# ── ONGLET 3 : Corriger ────────────────────────────────────────────
def _onglet_correction(utilisateur: dict):
    st.subheader("✏️ Corriger les travaux")
    st.caption("Sélectionnez un travail, ajoutez vos remarques et attribuez une note.")

    prof_id = utilisateur["uid"]
    travaux = Professeur.get_travaux_a_corriger(prof_id, statut="soumis")

    if not travaux:
        st.info("✅ Aucun travail en attente de correction.")
        return

    st.markdown(f"**{len(travaux)} travail(aux) à corriger**")

    for t in sorted(travaux, key=lambda x: x.get("date_soumis", ""), reverse=True):
        with st.expander(f"🆕 {t['eleve_nom']} | {t.get('classe','?')} | {t['matiere']} — {t.get('date_soumis','')[:10]}"):

            # Travail de l'élève
            st.markdown("**📄 Travail soumis :**")
            if t.get("contenu_texte"):
                st.text_area("Contenu", value=t["contenu_texte"],
                             height=200, disabled=True, key=f"corr_txt_{t['id']}")
            if t.get("fichier_url"):
                st.markdown(f"[📎 Ouvrir le fichier]({t['fichier_url']})")

            st.divider()

            # Formulaire de correction
            st.markdown("**✏️ Votre correction :**")
            note = st.number_input("Note /20", min_value=0.0, max_value=20.0,
                                   value=0.0, step=0.5, key=f"note_{t['id']}")
            remarques = st.text_area("Remarques détaillées",
                                      placeholder="Écrivez vos commentaires, points forts, points à améliorer...",
                                      height=150, key=f"rem_{t['id']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Enregistrer", key=f"save_{t['id']}", type="primary"):
                    if not remarques.strip():
                        st.warning("⚠️ Ajoutez des remarques avant d'enregistrer.")
                    else:
                        Travail.corriger(t["id"], note, remarques)
                        st.success("✅ Correction enregistrée !")
                        st.rerun()


# ── ONGLET 4 : Publier corrections ────────────────────────────────
def _onglet_publication(utilisateur: dict):
    st.subheader("✅ Publier les corrections")
    st.caption("Les corrections publiées deviennent visibles pour les élèves concernés uniquement.")

    prof_id          = utilisateur["uid"]
    travaux_corriges = Professeur.get_travaux_a_corriger(prof_id, statut="corrigé")

    if not travaux_corriges:
        st.info("📭 Aucune correction prête à publier. Corrigez d'abord les travaux.")
        return

    st.warning(f"⚠️ **{len(travaux_corriges)} correction(s)** prête(s) à être publiée(s).")

    with st.expander("👁️ Aperçu des corrections à publier"):
        for t in travaux_corriges:
            couleur = "green" if (t.get("note") or 0) >= 10 else "red"
            st.markdown(f"- **{t['eleve_nom']}** | {t.get('classe','?')} | {t['matiere']} | Note : **:{couleur}[{t.get('note','?')}/20]**")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Publier TOUTES les corrections", type="primary"):
            nb = Professeur.publier_corrections(prof_id)
            st.success(f"✅ {nb} correction(s) publiée(s) ! Les élèves peuvent voir leurs résultats.")
            st.balloons()
            st.rerun()

    with col2:
        st.info("💡 Les élèves ne voient leur note qu'après votre publication.")


# ── ONGLET 5 : Mes élèves ─────────────────────────────────────────
def _onglet_eleves(utilisateur: dict):
    st.subheader("👥 Mes élèves")

    prof_id = utilisateur["uid"]
    classes = ["Toutes"] + ["6e", "5e", "4e", "1ère", "Tle"]
    filtre  = st.selectbox("Filtrer par classe", classes, key="eleves_classe")

    classe_param = None if filtre == "Toutes" else filtre
    eleves       = Professeur.get_eleves(prof_id, classe=classe_param)

    if not eleves:
        st.info("Aucun élève inscrit pour le moment.")
        return

    st.markdown(f"**{len(eleves)} élève(s)**")

    for e in sorted(eleves, key=lambda x: x.get("classe", "")):
        en_ligne = "🟢 En ligne" if e.get("en_ligne") else "⚫ Hors ligne"
        with st.expander(f"🎓 {e['nom']} {e['prenom']} — {e.get('classe','?')} | {en_ligne}"):
            travaux_eleve = Professeur.get_travaux_a_corriger(prof_id, eleve_id=e["id"])
            publies       = [t for t in travaux_eleve if t.get("statut") == "publié" and t.get("note") is not None]
            notes         = [t["note"] for t in publies]
            moy           = f"{sum(notes)/len(notes):.1f}/20" if notes else "—"

            col1, col2, col3 = st.columns(3)
            col1.metric("Travaux soumis", len(travaux_eleve))
            col2.metric("Corrigés",       len(publies))
            col3.metric("Moyenne",        moy)

            # Difficultés détectées
            difficultes = e.get("difficultes", {})
            if difficultes:
                st.markdown("**⚠️ Difficultés détectées :**")
                for mat, diffi_list in difficultes.items():
                    if diffi_list:
                        st.markdown(f"- **{mat}** : {', '.join(diffi_list[:3])}")
