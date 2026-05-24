# auth/authentification.py
import streamlit as st
import datetime
import secrets
import requests as req
from config import get_db, initialiser_firebase
from firebase_admin import auth

db = None

def _db():
    global db
    if db is None:
        db = get_db()
    return db

def _timestamp() -> str:
    return datetime.datetime.now().isoformat()

# ── Connexion ──────────────────────────────────────────────────────
def connecter_utilisateur(email: str, mot_de_passe: str) -> dict | None:
    initialiser_firebase()
    api_key = st.secrets["FIREBASE_API_KEY"]
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {"email": email, "password": mot_de_passe, "returnSecureToken": True}
    try:
        reponse = req.post(url, json=payload)
        data = reponse.json()
        if "error" in data:
            return None
        uid = data["localId"]
        profil = _db().collection("users").document(uid).get().to_dict()
        if profil:
            profil["uid"] = uid
            # Mettre à jour le statut en ligne
            _db().collection("users").document(uid).update({
                "en_ligne": True,
                "derniere_connexion": _timestamp()
            })
            return profil
        return None
    except Exception:
        return None

def deconnecter() -> None:
    if est_connecte():
        uid = st.session_state.utilisateur.get("uid")
        if uid:
            try:
                _db().collection("users").document(uid).update({"en_ligne": False})
            except Exception:
                pass
    st.session_state.clear()

def est_connecte() -> bool:
    return "utilisateur" in st.session_state and st.session_state.utilisateur is not None

# ── Inscription élève ──────────────────────────────────────────────
def inscrire_eleve(prenom: str, nom: str, email: str, mot_de_passe: str,
                   telephone: str, classe: str, code_professeur: str) -> tuple[bool, str]:
    initialiser_firebase()
    prof_docs = list(
        _db().collection("users")
        .where("code_invitation", "==", code_professeur.strip().upper())
        .where("role", "==", "professeur")
        .stream()
    )
    if not prof_docs:
        return False, "Code professeur invalide. Contactez votre professeur."
    prof_id = prof_docs[0].id
    try:
        user = auth.create_user(email=email, password=mot_de_passe,
                                display_name=f"{nom} {prenom}",
                                phone_number=telephone if telephone.startswith("+") else None)
        profil = {
            "uid":           user.uid,
            "prenom":        prenom.strip().capitalize(),
            "nom":           nom.strip().upper(),
            "email":         email.strip().lower(),
            "telephone":     telephone.strip(),
            "role":          "eleve",
            "classe":        classe,
            "professeur_id": prof_id,
            "date_creation": _timestamp(),
            "en_ligne":      False,
            "difficultes":   {},
        }
        _db().collection("users").document(user.uid).set(profil)
        return True, "Compte créé avec succès !"
    except Exception as e:
        return False, f"Erreur : {str(e)}"

# ── Création compte (super_admin / admin) ──────────────────────────
def creer_compte(prenom: str, nom: str, email: str, mot_de_passe: str,
                 telephone: str, role: str, matieres: list[str] = None) -> tuple[bool, str]:
    initialiser_firebase()
    try:
        user = auth.create_user(email=email, password=mot_de_passe,
                                display_name=f"{nom} {prenom}")
        profil = {
            "uid":           user.uid,
            "prenom":        prenom.strip().capitalize(),
            "nom":           nom.strip().upper(),
            "email":         email.strip().lower(),
            "telephone":     telephone.strip(),
            "role":          role,
            "date_creation": _timestamp(),
            "en_ligne":      False,
        }
        if role == "professeur":
            profil["matieres"]        = matieres or []
            profil["code_invitation"] = secrets.token_hex(4).upper()
        _db().collection("users").document(user.uid).set(profil)
        return True, "Compte créé avec succès !"
    except Exception as e:
        return False, f"Erreur : {str(e)}"

# ── Réinitialisation mot de passe ──────────────────────────────────
def envoyer_reset_email(email: str) -> tuple[bool, str]:
    """Envoie un email de réinitialisation via Firebase."""
    initialiser_firebase()
    api_key = st.secrets["FIREBASE_API_KEY"]
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
    payload = {"requestType": "PASSWORD_RESET", "email": email}
    try:
        reponse = req.post(url, json=payload)
        data = reponse.json()
        if "error" in data:
            return False, "Email introuvable. Vérifiez votre adresse email."
        return True, "Email de réinitialisation envoyé ! Vérifiez votre boîte mail."
    except Exception as e:
        return False, f"Erreur : {str(e)}"

def changer_mot_de_passe(uid: str, nouveau_mdp: str) -> tuple[bool, str]:
    """Change le mot de passe directement."""
    initialiser_firebase()
    try:
        auth.update_user(uid, password=nouveau_mdp)
        return True, "Mot de passe modifié avec succès !"
    except Exception as e:
        return False, f"Erreur : {str(e)}"

def supprimer_compte(uid: str) -> tuple[bool, str]:
    initialiser_firebase()
    try:
        auth.delete_user(uid)
        _db().collection("users").document(uid).delete()
        return True, "Compte supprimé."
    except Exception as e:
        return False, f"Erreur : {str(e)}"
