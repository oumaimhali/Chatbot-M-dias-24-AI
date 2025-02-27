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

# Configuration de la page Streamlit
st.set_page_config(page_title="Assistant Médias 24", page_icon="🗞️", layout="wide")

# Configuration des clés API
if 'OPENAI_API_KEY' not in st.secrets:
    st.error("Veuillez configurer votre clé API OpenAI dans les secrets Streamlit.")
    st.stop()

# Configuration d'OpenAI
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])

# Configuration Elasticsearch
ES_URL = st.secrets.get('ELK_ENDPOINT', 'http://esmedias24.cloud.atlashoster.net:9200/')
ES_INDEX = st.secrets.get('ELK_INDEX', 'idxfnl')
ES_USERNAME = st.secrets.get('ELK_USERNAME', 'elastic')
ES_PASSWORD = st.secrets.get('ELK_PASSWORD', '')

if not ES_PASSWORD:
    st.error("Veuillez configurer les paramètres Elasticsearch dans les secrets Streamlit.")
    st.stop()

# Configuration de l'authentification Elasticsearch
ES_AUTH = (ES_USERNAME, ES_PASSWORD)
ES_TIMEOUT = 30  # Timeout en secondes

# Désactiver les avertissements SSL
urllib3.disable_warnings()

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
    """Génère une réponse basée sur les articles trouvés"""
    try:
        # Préparation du contexte
        context = "Voici les articles pertinents trouvés :\n\n"
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'Sans titre')
            content = article.get('content', '')
            date = article.get('date', '')
            context += f"Article {i}:\nTitre: {title}\nDate: {date}\nContenu: {content}\n\n"

        # Instruction pour le modèle
        system_prompt = """Tu es un assistant spécialisé dans l'analyse d'articles de Médias24. 
        Utilise les articles fournis pour répondre aux questions de manière précise et structurée.
        Si une chronologie est demandée, présente les événements de manière chronologique.
        Cite toujours tes sources en référençant les articles.
        Si tu ne trouves pas l'information dans les articles fournis, dis-le clairement."""

        # Appel à l'API OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {query}\n\nContexte: {context}"}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        # Extraction de la réponse
        return response.choices[0].message.content

    except Exception as e:
        st.error(f"Erreur lors de la génération de la réponse : {str(e)}")
        return "Désolé, je n'ai pas pu générer une réponse. Veuillez réessayer."

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
