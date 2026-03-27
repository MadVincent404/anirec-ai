# AniRec AI System

AniRec AI est un système de recommandation multi-agents pour les films, séries et animes. Il utilise un pipeline d'orchestration LLM (LangGraph + Groq) couplé à un moteur de filtrage haute performance (Polars) sur les bases de données IMDB et AniList. Un tableau de bord analytique permet également le suivi qualitatif des recommandations.

## Prérequis

- Python 3.11.9
- Une clé API Groq valide
- Les datasets bruts (IMDB et AniList)

## Installation

1. Clonez ce dépôt :
git clone <votre-url-de-repo>
cd anirec-ai

2. Créez un environnement virtuel et activez-le :
python -m venv .venv
source .venv/bin/activate  # Sur Windows: .venv\Scripts\activate

3. Installez les dépendances :
pip install -r requirements.txt

## Configuration

1. Créez un dossier `.streamlit` à la racine du projet et ajoutez un fichier `secrets.toml` contenant votre clé API :
GROQ_API_KEY = "votre_cle_api_groq_ici"

2. Assurez-vous que les fichiers de données suivants sont placés à la racine du projet (ou dans le chemin configuré) :
- anilist_anime_data_complete.csv
- title.basic.tsv
- title.ratings.tsv
- title.principals.tsv
- name.basics.tsv

## Utilisation

L'application est divisée en deux interfaces.

Pour lancer l'interface principale de recommandation :
streamlit run app.py

Pour lancer le tableau de bord d'analyse des retours utilisateurs :
streamlit run dashboard.py

## Structure du projet

- app.py : Interface utilisateur principale et gestion de session.
- agents_llm_graphe.py : Définition des agents LLM et du graphe d'exécution (LangGraph).
- data_manager_fichiers.py : Chargement, traitement et mise en cache des données avec Polars.
- dashboard.py : Interface d'analyse des feedbacks avec Altair et Pandas.
- config_et_secu.py : Configuration des chemins et sécurisation des inputs (protection contre les injections de prompt).