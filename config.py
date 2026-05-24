# config.py — Configuration Firebase
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
import streamlit as st

def initialiser_firebase():
    if not firebase_admin._apps:
        cle = {
            "type": "service_account",
            "project_id":                st.secrets["FIREBASE_PROJECT_ID"],
            "private_key_id":            st.secrets["FIREBASE_PRIVATE_KEY_ID"],
            "private_key":               st.secrets["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n"),
            "client_email":              st.secrets["FIREBASE_CLIENT_EMAIL"],
            "client_id":                 st.secrets["FIREBASE_CLIENT_ID"],
            "auth_uri":                  "https://accounts.google.com/o/oauth2/auth",
            "token_uri":                 "https://oauth2.googleapis.com/token",
        }
        cred = credentials.Certificate(cle)
        firebase_admin.initialize_app(cred, {
            "storageBucket": st.secrets["FIREBASE_STORAGE_BUCKET"]
        })

def get_db():
    initialiser_firebase()
    return firestore.client()

def get_bucket():
    initialiser_firebase()
    return storage.bucket()
