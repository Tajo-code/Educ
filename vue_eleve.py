# vues/vue_eleve.py — Espace élève (version corrigée)
import streamlit as st
from config import get_db, get_bucket
from models.travail import Travail, ExerciceQCM
from models.utilisateur import Eleve, Professeur
from utils.securite import exiger_role, verifier_acces_eleve, bloquer_acces_non_autorise


def afficher_vue_eleve():
    exiger_role(["eleve"])
    utilisateur = st.session_state.utilisateur

    if not verifier_acces_eleve(utilisateur["uid"]):
        bloquer_acces_non_autorise()

    # Vérifier si le prof est en ligne
    prof_id  = utilisateur.get("professeur_id", "")
    en_ligne = False
    if prof_id:
        prof_doc = get_db().collection("users").document(prof_id).get()
        if prof_doc.exists:
            en_ligne = prof_doc.to_dict().get("en_ligne", False)

    statut_prof = "🟢 Professeur en ligne" if en_ligne else "⚫ Professeur hors ligne"

    st.title(f"🎓 Bonjour, {utilisateur['prenom']} !")
    st.caption(f"Classe : {utilisateur['classe']}  •  {statut_prof}")

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "📂 Exercices",
        "🎯 Mes difficultés",
        "📋 Mes travaux",
        "📊 Ma progression",
    ])

    with onglet1:
        _onglet_exercices(utilisateur)
    with onglet2:
        _onglet_difficultes(utilisateur)
    with onglet3:
        _onglet_travaux(utilisateur)
    with onglet4:
        _onglet_progression(utilisateur)


# ── ONGLET 1 : Exercices publiés par le prof ──────────────────────
def _onglet_exercices(utilisateur: dict):
    st.subheader("📂 Exercices disponibles")
    st.caption("Voici les exercices publiés par votre professeur.")

    prof_id = utilisateur.get("professeur_id")
    classe  = utilisateur.get("classe")

    exercices = Professeur.get_exercices_publies(prof_id, classe=classe)

    if not exercices:
        st.info("📭 Aucun exercice disponible pour le moment. Revenez plus tard !")
        return

    for ex in sorted(exercices, key=lambda x: x.get("date_creation", ""), reverse=True):
        with st.expander(f"📌 {ex.get('titre','Sans titre')} — {ex.get('matiere','?')} | {ex.get('format','?')}"):
            st.markdown(f"**📋 Consignes :**")
            st.info(ex.get("consignes", "Pas de consignes."))

            if ex.get("contenu"):
                st.markdown("**📝 Exercice :**")
                st.markdown(ex["contenu"])

            if ex.get("fichier_url"):
                st.markdown(f"[📥 Télécharger le fichier]({ex['fichier_url']})")

            st.markdown(f"**📅 Date limite :** {ex.get('date_limite', '—')}")
            st.markdown(f"**📝 Format :** {ex.get('format', '—')}")

            st.divider()
            st.markdown("**✏️ Soumettre votre travail :**")

            mode = st.radio("Comment souhaitez-vous soumettre ?",
                            ["Écrire ici", "Uploader un fichier"],
                            horizontal=True, key=f"mode_{ex['id']}")

            if mode == "Écrire ici":
                contenu = st.text_area("Votre réponse", height=250,
                                        placeholder="Rédigez votre réponse ici...",
                                        key=f"contenu_{ex['id']}")
                if st.button("📤 Soumettre", type="primary", key=f"sub_{ex['id']}"):
                    if not contenu.strip():
                        st.warning("⚠️ Écrivez votre réponse avant de soumettre.")
                    else:
                        travail = Travail(
                            eleve_id=utilisateur["uid"],
                            eleve_nom=f"{utilisateur['nom']} {utilisateur['prenom']}",
                            prof_id=prof_id,
                            classe=classe,
                            matiere=ex.get("matiere", ""),
                            discipline=ex.get("titre", ""),
                            format_travail=ex.get("format", "Devoir individuel"),
                        )
                        travail.soumettre_texte(contenu)
                        st.success("✅ Travail soumis ! Votre professeur le corrigera bientôt.")

            else:
                fichier = st.file_uploader("Choisir un fichier",
                                            type=["pdf", "docx", "doc", "txt", "png", "jpg"],
                                            key=f"file_{ex['id']}")
                if fichier and st.button("📤 Soumettre", type="primary", key=f"fsub_{ex['id']}"):
                    travail = Travail(
                        eleve_id=utilisateur["uid"],
                        eleve_nom=f"{utilisateur['nom']} {utilisateur['prenom']}",
                        prof_id=prof_id,
                        classe=classe,
                        matiere=ex.get("matiere", ""),
                        discipline=ex.get("titre", ""),
                        format_travail=ex.get("format", "Devoir individuel"),
                    )
                    travail.soumettre_fichier(fichier.read(), fichier.name)
                    st.success("✅ Fichier soumis avec succès !")


# ── ONGLET 2 : Mes difficultés + exercices adaptés ────────────────
def _onglet_difficultes(utilisateur: dict):
    st.subheader("🎯 Mes difficultés et exercices adaptés")
    st.caption("Le système détecte vos difficultés et vous propose des exercices ciblés.")

    eleve_id = utilisateur["uid"]
    prof_id  = utilisateur.get("professeur_id")
    classe   = utilisateur.get("classe")

    difficultes = Eleve.get_difficultes(eleve_id)

    if not difficultes:
        st.info("✅ Aucune difficulté détectée pour le moment. Continuez à travailler !")
    else:
        st.warning("⚠️ Des difficultés ont été détectées dans ces matières :")
        for matiere, diffi_list in difficultes.items():
            if diffi_list:
                st.markdown(f"**{matiere} :** {', '.join(diffi_list)}")

    st.divider()

    # Questionnaire de diagnostic
    st.markdown("### 📝 Questionnaire de diagnostic")
    st.caption("Répondez à ce questionnaire pour que le système détecte vos difficultés.")

    matieres_dispo = ["Français", "Mathématiques", "Philosophie", "Physique-Chimie", "Histoire-Géo"]
    matiere_diag   = st.selectbox("Choisir une matière", matieres_dispo)

    # Exercices QCM adaptés
    exercices_adaptes = Eleve.get_exercices_adaptes(eleve_id, prof_id, classe)

    if exercices_adaptes:
        st.divider()
        st.markdown("### 📚 Exercices recommandés pour vous")
        for ex in exercices_adaptes:
            with st.expander(f"📌 {ex.get('titre', 'Exercice')} — {ex.get('matiere', '?')}"):
                questions = ex.get("questions", [])
                reponses  = {}

                for i, q in enumerate(questions):
                    st.markdown(f"**{i+1}. {q['question']}**")
                    choix = q.get("choix", [])
                    rep   = st.radio("", choix, key=f"qcm_{ex['id']}_{i}", index=None)
                    if rep:
                        reponses[q.get("id", str(i))] = rep

                if st.button("✅ Valider mes réponses", key=f"val_{ex['id']}", type="primary"):
                    if len(reponses) < len(questions):
                        st.warning("⚠️ Répondez à toutes les questions.")
                    else:
                        resultat = ExerciceQCM.corriger_automatiquement(
                            ex["id"], eleve_id, reponses
                        )
                        note = resultat["note"]
                        couleur = "green" if note >= 10 else "red"
                        st.markdown(f"### Votre note : :{couleur}[{note}/20]")
                        st.markdown(f"**{resultat['correctes']}/{resultat['total']}** réponses correctes")
                        if resultat["difficultes"]:
                            st.warning(f"Points à retravailler : {', '.join(resultat['difficultes'])}")
                        else:
                            st.success("🎉 Excellent ! Aucune difficulté détectée.")


# ── ONGLET 3 : Mes travaux soumis + corrections ───────────────────
def _onglet_travaux(utilisateur: dict):
    st.subheader("📋 Mes travaux soumis")

    eleve_id = utilisateur["uid"]

    if not verifier_acces_eleve(eleve_id):
        bloquer_acces_non_autorise()

    travaux = Eleve.get_travaux(eleve_id)

    if not travaux:
        st.info("📭 Vous n'avez encore soumis aucun travail.")
        return

    for t in sorted(travaux, key=lambda x: x.get("date_soumis", ""), reverse=True):
        statut = t.get("statut", "soumis")
        icone  = {"soumis": "🕐", "corrigé": "🔒", "publié": "✅"}.get(statut, "🕐")

        with st.expander(f"{icone} {t['matiere']} — {t.get('discipline','')} | {t.get('date_soumis','')[:10]} | {statut}"):
            if t.get("contenu_texte"):
                st.markdown("**Votre réponse :**")
                st.text(t["contenu_texte"])
            if t.get("fichier_url"):
                st.markdown(f"[📎 Voir le fichier]({t['fichier_url']})")

            st.divider()

            if statut == "publié":
                st.markdown("### 📝 Correction de votre professeur")
                note = t.get("note")
                if note is not None:
                    couleur = "green" if note >= 10 else "red"
                    st.markdown(f"**Note : :{couleur}[{note}/20]**")
                st.markdown(f"**Remarques :** {t.get('remarques', '—')}")
            else:
                st.info("🔒 La correction sera visible après publication par votre professeur.")


# ── ONGLET 4 : Progression ────────────────────────────────────────
def _onglet_progression(utilisateur: dict):
    st.subheader("📊 Ma progression")

    eleve_id = utilisateur["uid"]

    if not verifier_acces_eleve(eleve_id):
        bloquer_acces_non_autorise()

    travaux = Eleve.get_travaux(eleve_id)
    publies = [t for t in travaux if t.get("statut") == "publié" and t.get("note") is not None]

    col1, col2, col3 = st.columns(3)
    col1.metric("📤 Travaux soumis",  len(travaux))
    col2.metric("✅ Corrigés",         len(publies))
    col3.metric("⏳ En attente",       len(travaux) - len(publies))

    if publies:
        notes = [t["note"] for t in publies]
        moy   = sum(notes) / len(notes)
        couleur = "green" if moy >= 10 else "red"
        st.markdown(f"### Moyenne générale : :{couleur}[{moy:.1f} / 20]")

        st.divider()
        st.markdown("**📚 Détail par matière :**")
        matieres = {}
        for t in publies:
            m = t["matiere"]
            matieres.setdefault(m, []).append(t["note"])

        for mat, notes_mat in matieres.items():
            moy_mat = sum(notes_mat) / len(notes_mat)
            couleur = "green" if moy_mat >= 10 else "red"
            st.markdown(f"- **{mat}** : :{couleur}[{moy_mat:.1f}/20] ({len(notes_mat)} devoir(s))")

    # Difficultés
    difficultes = Eleve.get_difficultes(eleve_id)
    if difficultes:
        st.divider()
        st.markdown("**⚠️ Points à améliorer :**")
        for mat, diffi_list in difficultes.items():
            if diffi_list:
                st.markdown(f"- **{mat}** : {', '.join(diffi_list)}")
