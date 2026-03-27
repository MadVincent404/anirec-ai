import streamlit as st
import polars as pl
import csv
import json
import os
from datetime import datetime
from config_et_secu import directory_Path_for_data, fichier_feedback_csv_path, liste_Des_colonnes_pour_le_fichier_feedback

def sauvegarder_retour_utilisateur_dans_fichier_csv(
    identifiant_de_la_requete_id: str,
    requete_query_string: str,
    result_title_titre_du_resultat: str,
    result_source_origine: str,
    result_score_note_finale,
    thumbs_appreciation_pouce_en_l_air_ou_en_bas: str,
    precision_texte_optionnel: str = "",
):
    dictionnaire_de_la_ligne_a_ecrire = {
        "identifiant_unique":       identifiant_de_la_requete_id,
        "timestamp_horodatage":     datetime.utcnow().isoformat(timespec="seconds"),
        "query_requete":            requete_query_string,
        "result_title_titre":       result_title_titre_du_resultat,
        "result_source_provenance": result_source_origine,
        "result_score_note":        result_score_note_finale,
        "thumbs_appreciation":      thumbs_appreciation_pouce_en_l_air_ou_en_bas,
        "precision_details":        precision_texte_optionnel,
    }
    est_ce_que_le_fichier_existe_deja_boolean = os.path.exists(fichier_feedback_csv_path)
    with open(fichier_feedback_csv_path, "a", newline="", encoding="utf-8") as file_objet_fichier:
        writer_ecrivain_csv = csv.DictWriter(file_objet_fichier, fieldnames=liste_Des_colonnes_pour_le_fichier_feedback)
        if not est_ce_que_le_fichier_existe_deja_boolean:
            writer_ecrivain_csv.writeheader()
        writer_ecrivain_csv.writerow(dictionnaire_de_la_ligne_a_ecrire)


@st.cache_data(show_spinner="Chargement AniList data...")
def load_donnees_anilist_en_cache() -> list[dict]:
    chemin = os.path.join(directory_Path_for_data, "clean_anime.parquet")
    if not os.path.exists(chemin): return []
    return pl.read_parquet(chemin).to_dicts()

@st.cache_data(show_spinner="Chargement IMDB data...")
def load_donnees_imdb_en_cache() -> list[dict]:
    chemin = os.path.join(directory_Path_for_data, "clean_imdb.parquet")
    if not os.path.exists(chemin): return []
    return pl.read_parquet(chemin).to_dicts()

@st.cache_data(show_spinner="Chargement réalisateurs...")
def load_realisateurs_directors_imdb_en_cache() -> dict:
    chemin = os.path.join(directory_Path_for_data, "clean_directors.json")
    if not os.path.exists(chemin): return {}
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)