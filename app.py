import streamlit as st
import uuid
from config_et_secu import nettoyer_user_input_string_text
from data_manager_fichiers import (
    load_donnees_anilist_en_cache, 
    load_donnees_imdb_en_cache, 
    load_realisateurs_directors_imdb_en_cache,
    sauvegarder_retour_utilisateur_dans_fichier_csv
)
from agents_llm_graphe import construire_le_graphe_langgraph_complet

def afficher_interface_de_feedback_utilisateur_inline(identifiant_unique_query_id, texte_de_la_requete_query, choix_final_dictionnaire_choice):
    st.divider()
    cle_etat_feedback_envoye  = f"fb_sent_status_{identifiant_unique_query_id}"
    cle_etat_feedback_pouce = f"fb_thumb_status_{identifiant_unique_query_id}"

    if st.session_state.get(cle_etat_feedback_envoye):
        st.caption("Feedback enregistre avec succes.")
        return

    st.caption("Cette recommandation vous convient-elle ?")
    colonne_pour_le_bouton_oui, colonne_pour_le_bouton_non, _ = st.columns([1, 1, 6])
    with colonne_pour_le_bouton_oui:
        if st.button("Oui", key=f"up_bouton_{identifiant_unique_query_id}", use_container_width=True):
            st.session_state[cle_etat_feedback_pouce] = "up"
    with colonne_pour_le_bouton_non:
        if st.button("Non", key=f"down_bouton_{identifiant_unique_query_id}", use_container_width=True):
            st.session_state[cle_etat_feedback_pouce] = "down"

    if cle_etat_feedback_pouce in st.session_state:
        valeur_du_pouce_thumb = st.session_state[cle_etat_feedback_pouce]
        label_texte_a_afficher = "Positif" if valeur_du_pouce_thumb == "up" else "Negatif"
        st.caption(f"Appreciation actuelle : {label_texte_a_afficher}")
        precision_texte_saisi_par_user = st.text_area(
            "Precision supplementaire (optionnel)",
            placeholder="Ex : Le genre ne correspondait pas, mauvaise annee...",
            height=80,
            key=f"prec_champ_texte_{identifiant_unique_query_id}",
        )
        colonne_pour_bouton_envoyer, colonne_pour_bouton_ignorer = st.columns([1, 4])
        with colonne_pour_bouton_envoyer:
            if st.button("Envoyer le feedback", key=f"send_bouton_{identifiant_unique_query_id}", type="primary"):
                sauvegarder_retour_utilisateur_dans_fichier_csv(
                    identifiant_de_la_requete_id      = identifiant_unique_query_id,
                    requete_query_string         = texte_de_la_requete_query,
                    result_title_titre_du_resultat  = choix_final_dictionnaire_choice.get("title", ""),
                    result_source_origine = choix_final_dictionnaire_choice.get("source", ""),
                    result_score_note_finale  = choix_final_dictionnaire_choice.get("score", ""),
                    thumbs_appreciation_pouce_en_l_air_ou_en_bas        = valeur_du_pouce_thumb,
                    precision_texte_optionnel     = precision_texte_saisi_par_user.strip(),
                )
                st.session_state[cle_etat_feedback_envoye] = True
                del st.session_state[cle_etat_feedback_pouce]
                st.rerun()
        with colonne_pour_bouton_ignorer:
            if st.button("Ignorer l'etape", key=f"skip_bouton_{identifiant_unique_query_id}"):
                del st.session_state[cle_etat_feedback_pouce]
                st.rerun()

st.set_page_config(page_title="AniRec AI System", layout="wide")
st.title("AniRec AI — Recommandation Multi-Agents")
st.markdown("**LangGraph** + **Groq** + **AniList** & **IMDB**")

if "groq_key_api" not in st.session_state:
    st.session_state.groq_key_api = st.secrets["GROQ_API_KEY"]

if "dataframe_donnees_anime_global" not in st.session_state:
    st.session_state.dataframe_donnees_anime_global = load_donnees_anilist_en_cache()
if "dataframe_donnees_imdb_global" not in st.session_state:
    st.session_state.dataframe_donnees_imdb_global = load_donnees_imdb_en_cache()
if "dictionnaire_directors_map_global" not in st.session_state:
    st.session_state.dictionnaire_directors_map_global = load_realisateurs_directors_imdb_en_cache()

with st.sidebar:
    st.markdown(f"**Animes :** {len(st.session_state.dataframe_donnees_anime_global):,}")
    st.markdown(f"**Films/Series :** {len(st.session_state.dataframe_donnees_imdb_global):,}")

for cle_de_session, valeur_par_defaut_initiale in [
    ("liste_titres_exclus", []),
    ("derniere_requete_enregistree", ""),
    ("derniers_candidats_liste", []),
    ("dernier_resultat_tuple", None),
    ("identifiant_unique_resultat_id", None),
]:
    if cle_de_session not in st.session_state:
        st.session_state[cle_de_session] = valeur_par_defaut_initiale

def executer_le_pipeline_de_recommandation_complet(texte_requete_query: str, liste_titres_exclus_param: list):
    application_langgraph_compilee           = construire_le_graphe_langgraph_complet()
    etat_initial_du_systeme_dictionnaire = {
        "query": texte_requete_query, "excluded": liste_titres_exclus_param,
        "filters": {}, "candidates": [], "final_choice": {}, "critique": "",
    }
    critique_finale_texte_string, choix_final_dictionnaire, candidats_liste_complete = "", {}, []

    with st.status("Agents en cours d'execution...", expanded=True) as status_indicateur_ui:
        for output_donnees_en_sortie in application_langgraph_compilee.stream(etat_initial_du_systeme_dictionnaire):
            if "Agent_Profil_Node" in output_donnees_en_sortie:
                st.write("Agent Profil — Filtres extraits par le modele :")
                st.json(output_donnees_en_sortie["Agent_Profil_Node"]["filters"])
            elif "Agent_Similarite_Node" in output_donnees_en_sortie:
                choix_final_dictionnaire = output_donnees_en_sortie["Agent_Similarite_Node"]["final_choice"]
                candidats_liste_complete   = output_donnees_en_sortie["Agent_Similarite_Node"]["candidates"]
                st.write(
                    f"Agent Similarite — {len(candidats_liste_complete)} candidats trouves | "
                    f"Choix retenu : **{choix_final_dictionnaire['title']}** (score attribue : {choix_final_dictionnaire.get('score', '?')})"
                )
            elif "Agent_Critique_Node" in output_donnees_en_sortie:
                critique_finale_texte_string = output_donnees_en_sortie["Agent_Critique_Node"]["critique"]
                st.write("Agent Critique — Critique redigee avec succes.")
        status_indicateur_ui.update(label="Recommandation prete.", state="complete", expanded=False)

    return choix_final_dictionnaire, critique_finale_texte_string, candidats_liste_complete


texte_requete_brute_saisie_par_user = st.text_input(
    "Que voulez-vous regarder aujourd'hui ?",
    placeholder="Ex: Un film de Nolan, un anime fantasy bien note, une serie policiere apres 2015...",
)

texte_requete_nettoye_final = None
if texte_requete_brute_saisie_par_user:
    try:
        texte_requete_nettoye_final = nettoyer_user_input_string_text(texte_requete_brute_saisie_par_user)
    except ValueError as erreur_levee_pendant_sanitisation:
        st.error(str(erreur_levee_pendant_sanitisation))

if texte_requete_nettoye_final and texte_requete_nettoye_final != st.session_state.derniere_requete_enregistree:
    st.session_state.liste_titres_exclus = []
    st.session_state.derniere_requete_enregistree      = texte_requete_nettoye_final
    st.session_state.dernier_resultat_tuple     = None
    st.session_state.derniers_candidats_liste = []
    st.session_state.identifiant_unique_resultat_id       = None

if texte_requete_nettoye_final:
    if not st.session_state.dernier_resultat_tuple:
        choix_final_dictionnaire, critique_finale_texte_string, candidats_liste_complete = executer_le_pipeline_de_recommandation_complet(texte_requete_nettoye_final, st.session_state.liste_titres_exclus)
        st.session_state.dernier_resultat_tuple     = (choix_final_dictionnaire, critique_finale_texte_string)
        st.session_state.derniers_candidats_liste = candidats_liste_complete
        st.session_state.identifiant_unique_resultat_id       = str(uuid.uuid4())
        if choix_final_dictionnaire.get("title") and choix_final_dictionnaire["title"] != "Aucun resultat":
            st.session_state.liste_titres_exclus.append(choix_final_dictionnaire["title"])

    choix_final_dictionnaire, critique_finale_texte_string = st.session_state.dernier_resultat_tuple
    candidats_liste_complete       = st.session_state.derniers_candidats_liste
    identifiant_unique_resultat_id        = st.session_state.identifiant_unique_resultat_id

    st.markdown("---")
    if choix_final_dictionnaire.get("title"):
        annee_de_sortie_year_formatee = (
            int(choix_final_dictionnaire["year"])
            if choix_final_dictionnaire.get("year") and str(choix_final_dictionnaire.get("year")) not in ("nan", "None")
            else "?"
        )
        st.success(
            f"**{choix_final_dictionnaire['title']}** — "
            f"{str(choix_final_dictionnaire.get('source', '')).capitalize()} | "
            f"Score d'evaluation : {choix_final_dictionnaire.get('score', '?')} | "
            f"Annee de sortie : {annee_de_sortie_year_formatee} | "
            f"Genres associes : {choix_final_dictionnaire.get('genres', '-')}"
        )
    if critique_finale_texte_string:
        st.info(f"**Critique generee :**\n\n{critique_finale_texte_string}")

    autres_suggestions_liste_restreinte = [candidat for candidat in candidats_liste_complete[1:6] if candidat.get("title") != "Aucun resultat"]
    if autres_suggestions_liste_restreinte:
        st.markdown("**Autres suggestions potentielles :**")
        for item_candidat in autres_suggestions_liste_restreinte:
            annee_de_sortie_year_formatee = (
                int(item_candidat["year"])
                if item_candidat.get("year") and str(item_candidat.get("year")) not in ("nan", "None")
                else "?"
            )
            st.markdown(
                f"- **{item_candidat['title']}** ({str(item_candidat.get('source', '')).capitalize()}) "
                f"— Score : {item_candidat.get('score', '?')} | {annee_de_sortie_year_formatee} | {item_candidat.get('genres', '-')}"
            )

    afficher_interface_de_feedback_utilisateur_inline(identifiant_unique_resultat_id, texte_requete_nettoye_final, choix_final_dictionnaire)

    st.markdown("---")
    if st.button("Autres recommandations supplementaires (en tenant compte des precedentes)"):
        choix_final_dictionnaire, critique_finale_texte_string, candidats_liste_complete = executer_le_pipeline_de_recommandation_complet(texte_requete_nettoye_final, st.session_state.liste_titres_exclus)
        st.session_state.dernier_resultat_tuple     = (choix_final_dictionnaire, critique_finale_texte_string)
        st.session_state.derniers_candidats_liste = candidats_liste_complete
        st.session_state.identifiant_unique_resultat_id       = str(uuid.uuid4())
        if choix_final_dictionnaire.get("title") and choix_final_dictionnaire["title"] != "Aucun resultat":
            st.session_state.liste_titres_exclus.append(choix_final_dictionnaire["title"])
        st.rerun()

    if len(st.session_state.liste_titres_exclus) > 1:
        st.caption(f"Titres deja proposes et exclus : {', '.join(st.session_state.liste_titres_exclus)}")