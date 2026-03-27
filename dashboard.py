import streamlit as st
import pandas as pd
import os
import altair as alt
from datetime import datetime

directory_Path_for_data_system = os.path.dirname(os.path.abspath(__file__))
fichier_feedback_csv_path_absolu = os.path.join(directory_Path_for_data_system, "data", "feedback_anirec.csv")

st.set_page_config(
    page_title="AniRec — Dashboard Feedbacks Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# CHARGEMENT DES DONNEES EN CACHE
# ==========================================
@st.cache_data(ttl=30)
def Load_Les_Data_Depuis_CSV_Systeme() -> pd.DataFrame:
    liste_Des_colonnes_attendues_dans_le_fichier = [
        "identifiant_unique", "timestamp_horodatage", "query_requete", "result_title_titre",
        "result_source_provenance", "result_score_note", "thumbs_appreciation", "precision_details",
    ]
    
    est_ce_que_le_fichier_existe_boolean = os.path.exists(fichier_feedback_csv_path_absolu)
    
    if not est_ce_que_le_fichier_existe_boolean:
        return pd.DataFrame(columns=liste_Des_colonnes_attendues_dans_le_fichier)
    
    dictionnaire_De_typage_Pour_Pandas_Securite = {
        "query_requete": str,
        "result_title_titre": str,
        "result_source_provenance": str,
        "thumbs_appreciation": str,
        "precision_details": str
    }
    
    dataframe_donnees_feedback_brut = pd.read_csv(fichier_feedback_csv_path_absolu, encoding="utf-8", dtype=dictionnaire_De_typage_Pour_Pandas_Securite)
    
    dataframe_donnees_feedback_brut["timestamp_horodatage"] = pd.to_datetime(dataframe_donnees_feedback_brut["timestamp_horodatage"], errors="coerce")
    dataframe_donnees_feedback_brut["date_journee"] = dataframe_donnees_feedback_brut["timestamp_horodatage"].dt.date
    dataframe_donnees_feedback_brut["is_up_positif_boolean"] = dataframe_donnees_feedback_brut["thumbs_appreciation"] == "up"
    
    dataframe_donnees_feedback_brut["precision_details"] = dataframe_donnees_feedback_brut["precision_details"].fillna("")
    dataframe_donnees_feedback_brut["query_requete"] = dataframe_donnees_feedback_brut["query_requete"].fillna("")
    dataframe_donnees_feedback_brut["result_score_note"] = pd.to_numeric(dataframe_donnees_feedback_brut["result_score_note"], errors="coerce")
    
    return dataframe_donnees_feedback_brut


# ==========================================
# EN-TETE DASHBOARD
# ==========================================
st.title("AniRec — Dashboard Feedbacks Analytics")
st.caption(f"Source file : {fichier_feedback_csv_path_absolu}  —  refresh toutes les 30 secondes")
st.divider()

dataframe_Principal_Traite = Load_Les_Data_Depuis_CSV_Systeme()

if dataframe_Principal_Traite.empty:
    st.info("Aucun feedback enregistre pour le moment. Allez soumettre des appreciations.")
    st.stop()

# ==========================================
# FILTRES SIDEBAR
# ==========================================
with st.sidebar:
    st.header("Filtres Applicables")

    liste_sources_disponibles_pour_filtre = ["Toutes"] + sorted(dataframe_Principal_Traite["result_source_provenance"].dropna().unique().tolist())
    valeur_source_filtre_selectionnee = st.selectbox("Source de la data", liste_sources_disponibles_pour_filtre)

    dictionnaire_thumbs_options_mapping = {"Tous": None, "Positifs (oui)": "up", "Negatifs (non)": "down"}
    valeur_thumb_filtre_selectionnee = st.radio("Appreciation", list(dictionnaire_thumbs_options_mapping.keys()))

    if not dataframe_Principal_Traite["date_journee"].isna().all():
        date_minimum_trouvee_dans_dataset = dataframe_Principal_Traite["date_journee"].min()
        date_maximum_trouvee_dans_dataset = dataframe_Principal_Traite["date_journee"].max()
        
        valeur_par_defaut_pour_date_range = (date_minimum_trouvee_dans_dataset, date_maximum_trouvee_dans_dataset) if date_minimum_trouvee_dans_dataset != date_maximum_trouvee_dans_dataset else date_minimum_trouvee_dans_dataset
        
        Date_Range_selectionne_par_user = st.date_input(
            "Periode temporelle",
            value=valeur_par_defaut_pour_date_range,
            min_value=date_minimum_trouvee_dans_dataset,
            max_value=date_maximum_trouvee_dans_dataset,
        )
    else:
        Date_Range_selectionne_par_user = None

    st.divider()
    if st.button("Rafraichir les donnees cachees"):
        st.cache_data.clear()
        st.rerun()

dataframe_Filtre_Pour_Affichage = dataframe_Principal_Traite.copy()
# Application du filtre temporel avec verification de type securisee
if isinstance(Date_Range_selectionne_par_user, tuple):
    if len(Date_Range_selectionne_par_user) == 2:
        dataframe_Filtre_Pour_Affichage = dataframe_Filtre_Pour_Affichage[(dataframe_Filtre_Pour_Affichage["date_journee"] >= Date_Range_selectionne_par_user[0]) & (dataframe_Filtre_Pour_Affichage["date_journee"] <= Date_Range_selectionne_par_user[1])]
    elif len(Date_Range_selectionne_par_user) == 1:
        dataframe_Filtre_Pour_Affichage = dataframe_Filtre_Pour_Affichage[dataframe_Filtre_Pour_Affichage["date_journee"] == Date_Range_selectionne_par_user[0]]
elif Date_Range_selectionne_par_user is not None:
    dataframe_Filtre_Pour_Affichage = dataframe_Filtre_Pour_Affichage[dataframe_Filtre_Pour_Affichage["date_journee"] == Date_Range_selectionne_par_user]

# ==========================================
# KPIS METRICS
# ==========================================
nombre_total_de_lignes_filtrees = len(dataframe_Filtre_Pour_Affichage)
nombre_de_feedbacks_positifs = int(dataframe_Filtre_Pour_Affichage["is_up_positif_boolean"].sum())
nombre_de_feedbacks_negatifs = nombre_total_de_lignes_filtrees - nombre_de_feedbacks_positifs
taux_de_satisfaction_calcule_pourcentage = round(nombre_de_feedbacks_positifs / nombre_total_de_lignes_filtrees * 100, 1) if nombre_total_de_lignes_filtrees else 0
nombre_de_lignes_avec_precision_texte = int((dataframe_Filtre_Pour_Affichage["precision_details"].str.strip() != "").sum())

colonne_metric_un, colonne_metric_deux, colonne_metric_trois, colonne_metric_quatre, colonne_metric_cinq = st.columns(5)
colonne_metric_un.metric("Total feedbacks", nombre_total_de_lignes_filtrees)
colonne_metric_deux.metric("Positifs", nombre_de_feedbacks_positifs)
colonne_metric_trois.metric("Negatifs", nombre_de_feedbacks_negatifs)
colonne_metric_quatre.metric("Satisfaction globale", f"{taux_de_satisfaction_calcule_pourcentage} %")
colonne_metric_cinq.metric("Avec precision detaillee", nombre_de_lignes_avec_precision_texte)

st.divider()

# ==========================================
# GRAPHIQUES ALTAIR
# ==========================================
colonne_pour_le_graphique_un, colonne_pour_le_graphique_deux = st.columns(2)

with colonne_pour_le_graphique_un:
    st.subheader("Satisfaction par source de donnees")
    dataframe_statistiques_par_source_group = (
        dataframe_Filtre_Pour_Affichage.groupby(["result_source_provenance", "thumbs_appreciation"])
        .size()
        .reset_index(name="count_nombre")
    )
    if not dataframe_statistiques_par_source_group.empty:
        chart_altair_graphique = (
            alt.Chart(dataframe_statistiques_par_source_group)
            .mark_bar()
            .encode(
                x=alt.X("result_source_provenance:N", title="Source dataset", axis=alt.Axis(labelAngle=-20)),
                y=alt.Y("count_nombre:Q", title="Quantite"),
                color=alt.Color(
                    "thumbs_appreciation:N",
                    scale=alt.Scale(domain=["up", "down"], range=["#3ecf8e", "#e8624a"]),
                    legend=alt.Legend(title="Appreciation"),
                ),
                xOffset="thumbs_appreciation:N",
                tooltip=["result_source_provenance", "thumbs_appreciation", "count_nombre"],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_altair_graphique, use_container_width=True)
    else:
        st.caption("Pas de data pour ce graphique.")

with colonne_pour_le_graphique_deux:
    st.subheader("Evolution temporelle timeline")
    if dataframe_Filtre_Pour_Affichage["date_journee"].notna().any():
        dataframe_statistiques_journalieres = (
            dataframe_Filtre_Pour_Affichage.groupby(["date_journee", "thumbs_appreciation"])
            .size()
            .reset_index(name="count_nombre")
        )
        dataframe_statistiques_journalieres["date_journee"] = pd.to_datetime(dataframe_statistiques_journalieres["date_journee"])
        chart_altair_temporel_graph = (
            alt.Chart(dataframe_statistiques_journalieres)
            .mark_line(point=True)
            .encode(
                x=alt.X("date_journee:T", title="Date du jour"),
                y=alt.Y("count_nombre:Q", title="Quantite enregistree"),
                color=alt.Color(
                    "thumbs_appreciation:N",
                    scale=alt.Scale(domain=["up", "down"], range=["#3ecf8e", "#e8624a"]),
                    legend=alt.Legend(title="Appreciation"),
                ),
                tooltip=["date_journee:T", "thumbs_appreciation", "count_nombre"],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_altair_temporel_graph, use_container_width=True)
    else:
        st.caption("Pas de data temporelle disponible.")

st.divider()

# ==========================================
# TABLEAU DATAFRAME DETAILLE
# ==========================================
st.subheader("Feedbacks raw data details")

dataframe_Pour_Affichage_Dans_Le_Tableau_ui = dataframe_Filtre_Pour_Affichage.sort_values("timestamp_horodatage", ascending=False).copy()
dataframe_Pour_Affichage_Dans_Le_Tableau_ui["timestamp_horodatage"] = dataframe_Pour_Affichage_Dans_Le_Tableau_ui["timestamp_horodatage"].dt.strftime("%Y-%m-%d %H:%M").fillna("Date invalide format")
dataframe_Pour_Affichage_Dans_Le_Tableau_ui["query_requete"] = dataframe_Pour_Affichage_Dans_Le_Tableau_ui["query_requete"].str[:100]

st.dataframe(
    dataframe_Pour_Affichage_Dans_Le_Tableau_ui[[
        "timestamp_horodatage", "thumbs_appreciation", "result_source_provenance", "result_title_titre",
        "result_score_note", "query_requete", "precision_details",
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "timestamp_horodatage":     st.column_config.TextColumn("Date Time"),
        "thumbs_appreciation":        st.column_config.TextColumn("Appreciation user"),
        "result_source_provenance": st.column_config.TextColumn("Source d'origine"),
        "result_title_titre":  st.column_config.TextColumn("Titre suggere"),
        "result_score_note":  st.column_config.NumberColumn("Score evaluation", format="%.1f"),
        "query_requete":         st.column_config.TextColumn("Requete user input"),
        "precision_details":     st.column_config.TextColumn("Details supplementaires"),
    },
)

st.divider()

# ==========================================
# EXPORT DATA
# ==========================================
fichier_csv_encode_en_bytes = dataframe_Filtre_Pour_Affichage.to_csv(index=False).encode("utf-8")
st.download_button(
    label     = "Download les datas filtrees format CSV",
    data      = fichier_csv_encode_en_bytes,
    file_name = f"feedbacks_anirec_export_{datetime.utcnow().date()}.csv",
    mime      = "text/csv",
)