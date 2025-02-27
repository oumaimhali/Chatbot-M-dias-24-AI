import streamlit as st
import openai
from elasticsearch import Elasticsearch
from datetime import datetime
import json

# Configuration de OpenAI avec la clé API depuis Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Assistant Médias 24",
    page_icon="📰",
    layout="wide"
)

# Configuration Elasticsearch
def get_elasticsearch_client():
    try:
        es = Elasticsearch(
            st.secrets["ELK_ENDPOINT"],
            basic_auth=(st.secrets["ELK_USERNAME"], st.secrets["ELK_PASSWORD"]),
            verify_certs=False  # Pour le développement, à modifier en production
        )
        if not es.ping():
            st.error("Impossible de se connecter à Elasticsearch")
            return None
        return es
    except Exception as e:
        st.error(f"Erreur de connexion à Elasticsearch : {str(e)}")
        return None

# Fonction pour rechercher des articles
def search_articles(query, es_client):
    if not es_client:
        return []
    
    try:
        # Requête Elasticsearch
        search_query = {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"title": {"query": query, "boost": 3}}},
                        {"match": {"content": {"query": query, "boost": 2}}},
                        {"match": {"post_content": {"query": query, "boost": 2}}},
                        {"match_phrase": {"title": {"query": query, "boost": 4}}},
                        {"match_phrase": {"content": {"query": query, "boost": 3}}},
                        {"match_phrase": {"post_content": {"query": query, "boost": 3}}}
                    ]
                }
            },
            "size": 10,  # Nombre d'articles à retourner
            "sort": [{"_score": "desc"}]
        }
        
        response = es_client.search(
            index=st.secrets["ELK_INDEX"],
            body=search_query
        )
        
        articles = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            score = hit['_score']
            articles.append((source, score))
        
        return articles
    except Exception as e:
        st.error(f"Erreur lors de la recherche : {str(e)}")
        return []

# Titre de l'application
st.title("📰 Assistant Médias 24")
st.write("Je base mes réponses uniquement sur les articles de Médias 24.")

# Initialisation du client Elasticsearch
es_client = get_elasticsearch_client()

if es_client:
    # Zone de texte pour la saisie de l'utilisateur
    user_input = st.text_input("Posez votre question sur l'actualité :", key="user_input")

    # Traitement de la requête
    if user_input:
        # Recherche des articles pertinents
        relevant_articles = search_articles(user_input, es_client)
        
        if relevant_articles:
            # Affichage des articles trouvés
            st.write("---")
            st.subheader("Articles pertinents :")
            
            for article, score in relevant_articles:
                with st.expander(f"📰 {article.get('title', 'Sans titre')}"):
                    st.write(f"**Score de pertinence** : {score:.2f}")
                    st.write(f"**Titre** : {article.get('title', 'Sans titre')}")
                    st.write(f"**Contenu** : {article.get('content', 'Pas de contenu')}")
                    if article.get('post_content'):
                        st.write(f"**Contenu du post** : {article.get('post_content')}")
            
            # Préparation du contexte pour la réponse
            context = "Voici les articles pertinents de Médias 24 :\n\n"
            for article, score in relevant_articles:
                context += f"Titre: {article.get('title', 'Sans titre')}\n"
                context += f"Contenu: {article.get('content', 'Pas de contenu')}\n"
                if article.get('post_content'):
                    context += f"Contenu du post: {article.get('post_content')}\n"
                context += "\n"
            
            context += f"\nQuestion : {user_input}\n"
            context += "Fais une synthèse précise basée uniquement sur ces articles. Cite les titres des articles utilisés."
            
            try:
                # Génération de la synthèse
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Tu es un expert en analyse d'articles de Médias 24. Base tes réponses UNIQUEMENT sur les articles fournis. Si une information n'est pas dans les articles, dis-le clairement."},
                        {"role": "user", "content": context}
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                
                # Affichage de la synthèse
                st.write("---")
                st.subheader("Synthèse :")
                st.write(response.choices[0].message['content'])
                
            except Exception as e:
                st.error(f"Erreur lors de la génération de la synthèse : {str(e)}")
        else:
            st.warning("Je ne trouve pas d'articles pertinents sur ce sujet dans la base de Médias 24. Essayez une autre question ou reformulez votre demande.")
else:
    st.error("Le service est temporairement indisponible. Veuillez réessayer plus tard.")
