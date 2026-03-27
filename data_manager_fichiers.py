import streamlit as st
import polars as pl
import csv
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


@st.cache_data(show_spinner="Chargement AniList data en cours...")
def load_donnees_anilist_en_cache() -> list[dict]:
    dataframe_de_donnees_anime_temporaire = (
        pl.scan_csv(
            os.path.join(directory_Path_for_data, "anilist_anime_data_complete.csv"),
            infer_schema_length=1000,
        )
        .select([
            "title_english", "title_romaji", "genres",
            "averageScore", "description", "startDate_year", "popularity",
        ])
        .rename({
            "title_english": "title",
            "averageScore":  "score",
            "description":   "desc",
            "startDate_year": "year",
        })
        .with_columns([
            pl.when(pl.col("title").is_null() | (pl.col("title") == ""))
              .then(pl.col("title_romaji"))
              .otherwise(pl.col("title"))
              .alias("title"),
            pl.lit("anime").alias("source"),
            pl.col("genres").fill_null(""),
            pl.col("desc").fill_null("Pas de description."),
            pl.col("score").cast(pl.Float64, strict=False),
            pl.col("year").cast(pl.Float64, strict=False),
            pl.col("popularity").cast(pl.Float64, strict=False).fill_null(0.0),
        ])
        .filter(
            pl.col("title").is_not_null() &
            pl.col("score").is_not_null() &
            (pl.col("popularity") >= 500)
        )
        .select(["title", "source", "genres", "score", "desc", "year"])
        .collect()
    )
    return dataframe_de_donnees_anime_temporaire.to_dicts()


@st.cache_data(show_spinner="Chargement IMDB data en cours...")
def load_donnees_imdb_en_cache() -> list[dict]:
    dataframe_basics_informations = (
        pl.scan_csv(
            os.path.join(directory_Path_for_data, "title.basic.tsv"),
            separator="\t", null_values=["\\N"],
            infer_schema_length=1000, quote_char=None,
        )
        .select(["tconst", "titleType", "primaryTitle", "genres", "startYear"])
        .filter(pl.col("titleType").is_in(["movie", "tvSeries", "tvMiniSeries", "documentary"]))
    )
    dataframe_ratings_notes = (
        pl.scan_csv(
            os.path.join(directory_Path_for_data, "title.ratings.tsv"),
            separator="\t", null_values=["\\N"],
            infer_schema_length=1000, quote_char=None,
        )
        .select(["tconst", "averageRating", "numVotes"])
        .with_columns(pl.col("numVotes").cast(pl.Int64, strict=False))
        .filter(pl.col("numVotes") >= 10000)
    )
    dictionnaire_de_mapping_des_sources_types = {
        "movie": "film", "tvSeries": "serie",
        "tvMiniSeries": "serie", "documentary": "documentaire",
    }
    dataframe_final_fusionne = (
        dataframe_basics_informations.join(dataframe_ratings_notes, on="tconst", how="inner")
        .rename({"primaryTitle": "title", "averageRating": "score", "startYear": "year"})
        .with_columns([
            pl.col("titleType").replace(dictionnaire_de_mapping_des_sources_types).alias("source"),
            pl.col("genres").fill_null(""),
            pl.col("score").cast(pl.Float64, strict=False),
            pl.col("year").cast(pl.Float64, strict=False),
            pl.col("title").alias("desc"),
        ])
        .filter(pl.col("score").is_not_null())
        .select(["tconst", "title", "source", "genres", "score", "desc", "year"])
        .collect()
    )
    return dataframe_final_fusionne.to_dicts()


@st.cache_data(show_spinner="Chargement realisateurs IMDB data...")
def load_realisateurs_directors_imdb_en_cache() -> dict:
    dataframe_principals_equipe = (
        pl.scan_csv(
            os.path.join(directory_Path_for_data, "title.principals.tsv"),
            separator="\t", null_values=["\\N"],
            infer_schema_length=1000, quote_char=None,
        )
        .select(["tconst", "nconst", "category"])
        .filter(pl.col("category") == "director")
        .select(["tconst", "nconst"])
        .unique(subset=["tconst"])
    )
    dataframe_noms_des_personnes = (
        pl.scan_csv(
            os.path.join(directory_Path_for_data, "name.basics.tsv"),
            separator="\t", null_values=["\\N"],
            infer_schema_length=1000, quote_char=None,
        )
        .select(["nconst", "primaryName"])
    )
    dataframe_jointure_finale = (
        dataframe_principals_equipe.join(dataframe_noms_des_personnes, on="nconst", how="left")
        .select(["tconst", "primaryName"])
        .collect()
    )
    return dict(zip(dataframe_jointure_finale["tconst"].to_list(), dataframe_jointure_finale["primaryName"].to_list()))