# Chatbot Médias 24 AI

Un chatbot intelligent alimenté par l'IA pour interagir avec les articles de Médias 24.

## Fonctionnalités

- Interface utilisateur conviviale avec Streamlit
- Recherche intelligente d'articles avec Elasticsearch
- Génération de réponses naturelles avec OpenAI GPT
- Analyse et résumé d'articles
- Extraction de chronologies et d'événements clés

## Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/votre-username/Chatbot-Medias-24-AI.git
cd Chatbot-Medias-24-AI
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurer les variables d'environnement :
Créez un fichier `.env` avec :
```env
OPENAI_API_KEY=votre_clé_api_openai
ELASTIC_URL=votre_url_elasticsearch
ELASTIC_API_KEY=votre_clé_api_elasticsearch
```

## Utilisation

Lancer l'application :
```bash
streamlit run chatbot.py
```

## Déploiement

L'application est déployée sur Streamlit Cloud et accessible à :
[https://chatbot-medias-24-ai.streamlit.app](https://chatbot-medias-24-ai.streamlit.app)

## Technologies

- [Streamlit](https://streamlit.io/) - Interface utilisateur
- [OpenAI GPT](https://openai.com/) - Génération de réponses
- [Elasticsearch](https://www.elastic.co/) - Recherche d'articles
- [Python](https://www.python.org/) - Langage de programmation

## Auteur

- Oumaima Halim
