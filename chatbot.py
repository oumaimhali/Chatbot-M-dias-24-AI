import streamlit as st
import openai
import pandas as pd
from datetime import datetime

# Configuration de OpenAI avec la clé API depuis Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Assistant Articles Médias",
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
    if df is None:
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
    return [(df.loc[idx], score) for idx, score in scores[:5]]  # Top 5 articles

# Initialisation de l'historique des messages
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": """Tu es un assistant spécialisé dans l'analyse d'articles de presse.
        Tu dois :
        1. Baser tes réponses uniquement sur les articles fournis
        2. Citer les sources des articles quand tu réponds
        3. Être précis et factuel
        4. Si aucun article ne correspond à la question, le dire clairement
        5. Synthétiser l'information de manière claire et structurée"""}
    ]

# Titre de l'application
st.title("💬 Assistant Articles Médias Intelligent")

# Chargement des données
df = load_data()

# Zone de texte pour la saisie de l'utilisateur
user_input = st.text_input("Posez votre question sur les articles :", key="user_input")

# Traitement de la requête
if user_input:
    # Ajout du message de l'utilisateur à l'historique
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Recherche des articles pertinents
    relevant_articles = find_relevant_articles(user_input, df)
    
    if relevant_articles:
        # Préparation du contexte avec les articles trouvés
        context = "Voici les articles pertinents pour répondre à la question :\n\n"
        for article, score in relevant_articles:
            context += f"Date: {article['Date'].strftime('%d/%m/%Y')}\n"
            context += f"Titre: {article['Titre']}\n"
            context += f"Contenu: {article['Contenu']}\n\n"
        
        # Ajout de la question de l'utilisateur
        context += f"\nQuestion de l'utilisateur : {user_input}\n"
        context += "Réponds en te basant uniquement sur ces articles. Cite les sources (date et titre) dans ta réponse."
        
        try:
            # Obtention de la réponse
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Tu es un expert en analyse d'articles de presse. Base tes réponses uniquement sur les articles fournis et cite tes sources."},
                    {"role": "user", "content": context}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            # Ajout de la réponse à l'historique
            assistant_response = response.choices[0].message['content']
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            
        except Exception as e:
            st.error(f"Erreur lors de la génération de la réponse : {str(e)}")
    else:
        no_articles_response = "Je ne trouve pas d'articles pertinents sur ce sujet dans notre base de données. Pourriez-vous reformuler votre question ou choisir un autre sujet ?"
        st.session_state.messages.append({"role": "assistant", "content": no_articles_response})

# Affichage de l'historique des messages
st.write("---")
st.subheader("Conversation :")
for message in st.session_state.messages[1:]:  # Skip the system message
    if message["role"] == "user":
        st.write("👤 Vous :")
        st.write(message["content"])
    else:
        st.write("🤖 Assistant :")
        st.write(message["content"])
    st.write("---")
