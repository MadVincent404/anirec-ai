import polars as pl
import os
import json

def preparer_et_sauvegarder_donnees():
    dossier_data = os.path.dirname(os.path.abspath(__file__))
    
    print("Traitement AniList...")
    df_anime = (
        pl.scan_csv(os.path.join(dossier_data, "anilist_anime_data_complete.csv"), infer_schema_length=1000)
        .select(["title_english", "title_romaji", "genres", "averageScore", "description", "startDate_year", "popularity"])
        .rename({"title_english": "title", "averageScore": "score", "description": "desc", "startDate_year": "year"})
        .with_columns([
            pl.when(pl.col("title").is_null() | (pl.col("title") == "")).then(pl.col("title_romaji")).otherwise(pl.col("title")).alias("title"),
            pl.lit("anime").alias("source"),
            pl.col("genres").fill_null(""),
            pl.col("desc").fill_null("Pas de description."),
            pl.col("score").cast(pl.Float64, strict=False),
            pl.col("year").cast(pl.Float64, strict=False),
            pl.col("popularity").cast(pl.Float64, strict=False).fill_null(0.0),
        ])
        .filter(pl.col("title").is_not_null() & pl.col("score").is_not_null() & (pl.col("popularity") >= 500))
        .select(["title", "source", "genres", "score", "desc", "year"])
        .collect()
    )
    df_anime.write_parquet(os.path.join(dossier_data, "clean_anime.parquet"))

    print("Traitement IMDB (Films/Séries)...")
    df_basics = pl.scan_csv(os.path.join(dossier_data, "title.basic.tsv"), separator="\t", null_values=["\\N"], infer_schema_length=1000, quote_char=None).select(["tconst", "titleType", "primaryTitle", "genres", "startYear"]).filter(pl.col("titleType").is_in(["movie", "tvSeries", "tvMiniSeries", "documentary"]))
    df_ratings = pl.scan_csv(os.path.join(dossier_data, "title.ratings.tsv"), separator="\t", null_values=["\\N"], infer_schema_length=1000, quote_char=None).select(["tconst", "averageRating", "numVotes"]).with_columns(pl.col("numVotes").cast(pl.Int64, strict=False)).filter(pl.col("numVotes") >= 10000)
    
    map_sources = {"movie": "film", "tvSeries": "serie", "tvMiniSeries": "serie", "documentary": "documentaire"}
    df_imdb = (
        df_basics.join(df_ratings, on="tconst", how="inner")
        .rename({"primaryTitle": "title", "averageRating": "score", "startYear": "year"})
        .with_columns([
            pl.col("titleType").replace(map_sources).alias("source"),
            pl.col("genres").fill_null(""),
            pl.col("score").cast(pl.Float64, strict=False),
            pl.col("year").cast(pl.Float64, strict=False),
            pl.col("title").alias("desc")
        ])
        .filter(pl.col("score").is_not_null())
        .select(["tconst", "title", "source", "genres", "score", "desc", "year"])
        .collect()
    )
    df_imdb.write_parquet(os.path.join(dossier_data, "clean_imdb.parquet"))

    print("Traitement IMDB (Réalisateurs)...")
    tconst_valides = df_imdb["tconst"].to_list()
    df_principals = pl.scan_csv(os.path.join(dossier_data, "title.principals.tsv"), separator="\t", null_values=["\\N"], infer_schema_length=1000, quote_char=None).select(["tconst", "nconst", "category"]).filter(pl.col("category") == "director").select(["tconst", "nconst"]).unique(subset=["tconst"]).filter(pl.col("tconst").is_in(tconst_valides))
    df_names = pl.scan_csv(os.path.join(dossier_data, "name.basics.tsv"), separator="\t", null_values=["\\N"], infer_schema_length=1000, quote_char=None).select(["nconst", "primaryName"])
    
    df_directors = df_principals.join(df_names, on="nconst", how="left").select(["tconst", "primaryName"]).collect()
    dict_directors = dict(zip(df_directors["tconst"].to_list(), df_directors["primaryName"].to_list()))
    
    with open(os.path.join(dossier_data, "clean_directors.json"), "w", encoding="utf-8") as f:
        json.dump(dict_directors, f)

    print("Terminé. Les fichiers .parquet et .json ont été créés.")

if __name__ == "__main__":
    preparer_et_sauvegarder_donnees()