import streamlit as st
import openai
from openai import OpenAI
import requests
import json
import urllib3
from datetime import datetime
import re
from typing import List, Dict
from collections import defaultdict

# Configuration de la page Streamlit (doit être en premier)
st.set_page_config(page_title="Assistant Médias 24", page_icon="🗞️", layout="wide")

# Désactiver les avertissements SSL
urllib3.disable_warnings()

# Configuration
ES_URL = "https://esmedias24.cloud.atlashoster.net:9200"  # Changé pour HTTPS
ES_INDEX = "idxfnl"
ES_AUTH = ("elastic", "Zo501nQV7AKxxxxxx")
ES_TIMEOUT = 30  # Timeout en secondes

# Configuration OpenAI
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"Erreur de configuration: {str(e)}")
    st.error("Veuillez configurer votre clé API dans .streamlit/secrets.toml")

def test_elasticsearch_connection():
    """Test la connexion à Elasticsearch"""
    try:
        response = requests.get(
            ES_URL,
            auth=ES_AUTH,
            verify=False,
            timeout=ES_TIMEOUT
        )
        if response.ok:
            st.success("✅ Connexion à Elasticsearch établie")
            return True
        else:
            st.error(f"❌ Erreur de connexion à Elasticsearch: {response.text}")
            return False
    except requests.exceptions.ConnectTimeout:
        st.error("❌ Délai d'attente dépassé lors de la connexion à Elasticsearch")
        return False
    except requests.exceptions.ConnectionError:
        st.error("❌ Impossible de se connecter au serveur Elasticsearch")
        return False
    except Exception as e:
        st.error(f"❌ Erreur inattendue: {str(e)}")
        return False

def extract_keywords(query: str) -> List[str]:
    """Extrait les mots-clés importants de la requête"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Extrais les mots-clés importants de cette requête, en les séparant par des virgules. "
                              "Inclus les noms propres, les dates, les lieux et les concepts importants."
                },
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            max_tokens=100
        )
        keywords = response.choices[0].message.content.split(',')
        return [k.strip() for k in keywords if k.strip()]
    except Exception as e:
        st.warning(f"Erreur lors de l'extraction des mots-clés: {str(e)}")
        return [query]

def search_articles(query: str, size: int = 10) -> List[Dict]:
    """Recherche avancée des articles dans Elasticsearch"""
    if not test_elasticsearch_connection():
        return []

    keywords = extract_keywords(query)
    
    search_body = {
        "query": {
            "bool": {
                "should": [
                    {"match_phrase": {"post_title": {"query": kw, "boost": 4}}} for kw in keywords
                ] + [
                    {"match_phrase": {"summary": {"query": kw, "boost": 3}}} for kw in keywords
                ],
                "minimum_should_match": 1
            }
        },
        "size": size,
        "_source": ["post_title", "summary", "lien1", "date"],
        "sort": [
            {"_score": "desc"},
            {"date": "desc"}
        ]
    }
    
    try:
        response = requests.post(
            f"{ES_URL}/{ES_INDEX}/_search",
            auth=ES_AUTH,
            json=search_body,
            verify=False,
            timeout=ES_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        
        if response.ok:
            results = response.json()
            articles = []
            
            for hit in results.get("hits", {}).get("hits", []):
                source = hit.get("_source", {})
                articles.append({
                    "title": source.get("post_title", ""),
                    "content": source.get("summary", ""),
                    "url": source.get("lien1", ""),
                    "published_at": source.get("date", ""),
                    "score": hit.get("_score", 0)
                })
            
            if not articles:
                st.warning("Aucun article trouvé pour cette requête.")
            else:
                st.success(f"{len(articles)} articles trouvés")
            
            return articles
        else:
            st.error(f"Erreur Elasticsearch: {response.text}")
            return []
            
    except requests.exceptions.ConnectTimeout:
        st.error("Délai d'attente dépassé lors de la recherche. Veuillez réessayer.")
        return []
    except requests.exceptions.ConnectionError:
        st.error("Impossible de se connecter au serveur Elasticsearch. Veuillez vérifier votre connexion.")
        return []
    except Exception as e:
        st.error(f"Erreur lors de la recherche: {str(e)}")
        return []

def analyze_articles(articles: List[Dict]) -> Dict:
    """Analyse les articles pour extraire des informations clés"""
    analysis = {
        "timeline": defaultdict(list),
        "key_topics": defaultdict(int),
        "sources": set(),
        "date_range": {"start": None, "end": None}
    }
    
    for article in articles:
        # Timeline
        date = article.get("published_at", "").split("T")[0]
        if date:
            analysis["timeline"][date].append(article)
        
        # Sources
        if article.get("url"):
            analysis["sources"].add(article["url"])
        
        # Update date range
        if date:
            if not analysis["date_range"]["start"] or date < analysis["date_range"]["start"]:
                analysis["date_range"]["start"] = date
            if not analysis["date_range"]["end"] or date > analysis["date_range"]["end"]:
                analysis["date_range"]["end"] = date
    
    return analysis

def get_ai_response(query: str, articles: List[Dict]) -> str:
    """Génère une réponse détaillée et structurée"""
    if not articles:
        return "Je n'ai pas trouvé d'articles pertinents pour répondre à votre question."
    
    try:
        # Analyse des articles
        analysis = analyze_articles(articles)
        
        # Création du contexte
        context = f"""Informations sur les articles trouvés:
1. Période couverte: du {analysis['date_range']['start']} au {analysis['date_range']['end']}
2. Nombre d'articles: {len(articles)}
3. Sources: {len(analysis['sources'])} articles uniques

Articles par ordre chronologique:
"""
        
        for date, date_articles in sorted(analysis["timeline"].items()):
            context += f"\n{date}:\n"
            for article in date_articles:
                context += f"- {article['title']}\n"
                context += f"  {article['content'][:200]}...\n"

        messages = [
            {
                "role": "system",
                "content": """Tu es l'Assistant Médias 24, un expert en analyse d'actualités marocaines.
                Ton objectif est de fournir des réponses détaillées, précises et bien structurées.
                
                Directives pour tes réponses:
                1. Commence par un bref résumé de la situation
                2. Présente les événements de manière chronologique
                3. Mets en évidence les dates et faits importants
                4. Identifie les tendances et développements clés
                5. Fournis une analyse approfondie
                6. Cite tes sources avec précision
                7. Conclus avec une synthèse globale
                
                Format de réponse:
                Résumé
                Chronologie des événements
                Points clés
                Analyse
                Sources
                """
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nContexte:\n{context}"
            }
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo-16k",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content

    except Exception as e:
        st.error(f"Erreur lors de la génération de la réponse: {str(e)}")
        return "Désolé, je ne peux pas générer une réponse pour le moment."

# Interface Streamlit
st.title("Assistant Médias 24 ")
st.markdown("""
### Un assistant intelligent spécialisé dans l'actualité marocaine

Je peux vous aider à :
- Analyser en profondeur les sujets d'actualité
- Créer des chronologies détaillées des événements
- Identifier les tendances et développements clés
- Fournir des analyses contextuelles approfondies
""")

# Zone de saisie utilisateur
query = st.text_input("Posez votre question ou indiquez le sujet qui vous intéresse :")

# Paramètres de recherche
col1, col2 = st.columns(2)
with col1:
    max_results = st.slider("Nombre d'articles à analyser", min_value=5, max_value=50, value=20)
with col2:
    sort_by = st.selectbox(
        "Trier les résultats par",
        ["Pertinence et date", "Date uniquement", "Pertinence uniquement"]
    )

if query:
    with st.spinner(" Recherche et analyse approfondie en cours..."):
        # Recherche des articles
        articles = search_articles(query, size=max_results)
        
        if articles:
            # Tri des articles selon le choix de l'utilisateur
            if sort_by == "Date uniquement":
                articles.sort(key=lambda x: x["published_at"], reverse=True)
            elif sort_by == "Pertinence uniquement":
                articles.sort(key=lambda x: x["score"], reverse=True)
            
            # Afficher la réponse générée
            response = get_ai_response(query, articles)
            st.markdown(response)
            
            # Afficher les sources
            with st.expander("Consulter les articles sources"):
                for article in articles:
                    st.markdown(f"""
                    **{article['published_at'].split('T')[0]}** - [{article['title']}]({article['url']})  
                    {article['content'][:200]}...
                    """)
        else:
            st.warning("Aucun article trouvé pour cette requête.")
