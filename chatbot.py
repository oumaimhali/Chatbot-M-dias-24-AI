import streamlit as st
import openai
import pandas as pd
from datetime import datetime

# Configuration de OpenAI avec la clé API depuis Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Assistant Médias 24",
    page_icon="📰",
    layout="wide"
)

# Chargement des données
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("data/articles_demo.xlsx")
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        return df.sort_values('Date', ascending=True)
    except Exception as e:
        st.error(f"Erreur de chargement des articles : {str(e)}")
        return None

# Fonction pour trouver les articles pertinents
def find_relevant_articles(query, df):
    if df is None or not query:
        return []
    
    query = query.lower()
    scores = []
    
    for idx, row in df.iterrows():
        content = str(row.get('Contenu', '')).lower()
        title = str(row.get('Titre', '')).lower()
        title_score = sum(word in title for word in query.split()) * 2
        content_score = sum(word in content for word in query.split())
        total_score = title_score + content_score
        if total_score > 0:
            scores.append((idx, total_score))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    return [(df.loc[idx], score) for idx, score in scores]  # Retourner tous les articles pertinents

# Titre de l'application
st.title("📰 Assistant Médias 24")
st.write("Je base mes réponses uniquement sur les articles de Médias 24.")

# Chargement des données
df = load_data()

# Zone de texte pour la saisie de l'utilisateur
user_input = st.text_input("Posez votre question sur l'actualité :", key="user_input")

# Traitement de la requête
if user_input:
    # Recherche des articles pertinents
    relevant_articles = find_relevant_articles(user_input, df)
    
    if relevant_articles:
        # Affichage des articles trouvés
        st.write("---")
        st.subheader("Articles pertinents :")
        
        for article, score in sorted(relevant_articles, key=lambda x: x[0]['Date'], reverse=True):
            with st.expander(f"📰 {article['Date'].strftime('%d/%m/%Y')} - {article['Titre']}"):
                st.write(f"**Date** : {article['Date'].strftime('%d/%m/%Y')}")
                st.write(f"**Titre** : {article['Titre']}")
                st.write(f"**Contenu** : {article['Contenu']}")
        
        # Préparation du contexte pour la réponse
        context = "Voici les articles pertinents de Médias 24 :\n\n"
        for article, score in relevant_articles:
            context += f"Date: {article['Date'].strftime('%d/%m/%Y')}\n"
            context += f"Titre: {article['Titre']}\n"
            context += f"Contenu: {article['Contenu']}\n\n"
        
        context += f"\nQuestion : {user_input}\n"
        context += "Fais une synthèse précise basée uniquement sur ces articles. Cite les dates et titres des articles utilisés."
        
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
