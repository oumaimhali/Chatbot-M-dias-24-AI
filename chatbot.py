import streamlit as st
import openai
import pandas as pd
from datetime import datetime

# Configuration de OpenAI avec la clé API depuis Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Assistant Conversationnel",
    page_icon="💬",
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
    return [(df.loc[idx], score) for idx, score in scores[:3]]  # Top 3 articles les plus pertinents

# Initialisation de l'historique des messages
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": """Tu es un assistant conversationnel intelligent qui a accès à une base d'articles de presse.
        Tu dois :
        1. Être amical et naturel dans tes réponses
        2. Utiliser les articles comme source d'information quand c'est pertinent
        3. Pouvoir aussi répondre à des questions générales
        4. Maintenir une conversation fluide
        5. Si la question porte sur l'actualité ou l'économie, chercher dans les articles
        6. Pour les autres sujets, répondre de manière générale
        
        Réponds toujours en français et de manière naturelle."""}
    ]

# Titre de l'application
st.title("💬 Assistant Conversationnel Intelligent")

# Chargement des données
df = load_data()

# Zone de texte pour la saisie de l'utilisateur
user_input = st.text_input("Discutons ! Je peux vous parler de l'actualité ou d'autres sujets :", key="user_input")

# Traitement de la requête
if user_input:
    # Ajout du message de l'utilisateur à l'historique
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Recherche des articles pertinents
    relevant_articles = find_relevant_articles(user_input, df)
    
    try:
        if relevant_articles:
            # Si des articles pertinents sont trouvés, les inclure dans le contexte
            context = "Pour répondre à cette question, voici des articles pertinents :\n\n"
            for article, score in relevant_articles:
                context += f"Date: {article['Date'].strftime('%d/%m/%Y')}\n"
                context += f"Titre: {article['Titre']}\n"
                context += f"Contenu: {article['Contenu']}\n\n"
            
            context += f"\nQuestion de l'utilisateur : {user_input}\n"
            context += "Réponds de manière naturelle et conversationnelle, en utilisant ces informations si elles sont pertinentes."
            
            messages = [
                {"role": "system", "content": "Tu es un assistant conversationnel amical qui a accès à des articles de presse. Utilise ces informations naturellement dans la conversation quand c'est pertinent."},
                {"role": "user", "content": context}
            ]
        else:
            # Si pas d'articles pertinents, conversation normale
            messages = st.session_state.messages + [{"role": "user", "content": user_input}]
        
        # Obtention de la réponse
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        # Ajout de la réponse à l'historique
        assistant_response = response.choices[0].message['content']
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        
    except Exception as e:
        st.error(f"Erreur lors de la génération de la réponse : {str(e)}")

# Affichage de l'historique des messages
st.write("---")
st.subheader("Notre conversation :")
for message in st.session_state.messages[1:]:  # Skip the system message
    if message["role"] == "user":
        st.write("👤 Vous :")
        st.write(message["content"])
    else:
        st.write("🤖 Assistant :")
        st.write(message["content"])
    st.write("---")
