from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import urllib3
import streamlit as st
import openai

# Désactiver les avertissements SSL
urllib3.disable_warnings()

# Configuration
ES_URL = "http://esmedias24.cloud.atlashoster.net:9200"
ES_INDEX = "idxfnl"
ES_AUTH = ("elastic", "Zo501nQV7AKxxxxxx")

# Configuration OpenAI
openai.api_key = st.secrets["OPENAI_API_KEY"]

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"message": "Bienvenue sur l'API de l'Assistant Médias 24"})

@app.route('/health')
def health_check():
    """Vérifie la santé de l'API et la connexion à Elasticsearch"""
    try:
        response = requests.get(ES_URL, auth=ES_AUTH, verify=False)
        if response.ok:
            return jsonify({"status": "healthy", "elasticsearch": "connected"})
        return jsonify({"status": "healthy", "elasticsearch": "error"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def search_articles(query):
    """Recherche des articles dans Elasticsearch"""
    search_url = f"{ES_URL}/{ES_INDEX}/_search"
    search_body = {
        "query": {
            "bool": {
                "should": [
                    {"match_phrase": {"post_title": {"query": query, "boost": 4}}},
                    {"match_phrase": {"summary": {"query": query, "boost": 3}}}
                ]
            }
        },
        "size": 5,
        "_source": ["post_title", "summary", "lien1", "date"],
        "sort": [{"_score": "desc"}]
    }
    
    try:
        response = requests.post(
            search_url,
            auth=ES_AUTH,
            json=search_body,
            verify=False,
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
                    "published_at": source.get("date", "")
                })
            
            return articles
        else:
            print(f"Erreur Elasticsearch: {response.text}")
            return []
            
    except Exception as e:
        print(f"Erreur lors de la recherche: {str(e)}")
        return []

@app.route('/chat', methods=['POST'])
def chat():
    """Génère une réponse basée sur les articles trouvés"""
    data = request.json
    query = data.get('text', '')
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
        
    articles = search_articles(query)
    
    if not articles:
        return jsonify({
            "response": "Je n'ai pas trouvé d'articles pertinents pour répondre à votre question.",
            "articles": []
        })
    
    try:
        context = "Articles pertinents:\n\n"
        for article in articles:
            context += f"Titre: {article['title']}\n"
            context += f"Contenu: {article['content']}\n\n"

        messages = [
            {
                "role": "system",
                "content": "Vous êtes l'Assistant Médias 24, spécialisé dans l'actualité marocaine. "
                          "Répondez aux questions en vous basant uniquement sur les articles fournis. "
                          "Si les articles ne contiennent pas assez d'informations, dites-le clairement."
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}\n\n"
                          "Répondez à la question en vous basant uniquement sur les articles fournis."
            }
        ]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        return jsonify({
            "response": response.choices[0].message['content'],
            "articles": articles
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Démarrage du serveur sur http://localhost:8000")
    app.run(host='0.0.0.0', port=8000, debug=True)
