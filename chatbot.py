import streamlit as st
import openai
from datetime import datetime

# Configuration de OpenAI avec la clé API depuis Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Chatbot Intelligent",
    page_icon="💬",
    layout="wide"
)

# Initialisation de l'historique des messages s'il n'existe pas
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": """Tu es un assistant conversationnel intelligent et amical. 
        Tu dois être :
        1. Poli et professionnel
        2. Capable de répondre à une variété de sujets
        3. Précis dans tes réponses
        4. Capable de poser des questions pour mieux comprendre les besoins de l'utilisateur
        5. En mesure de fournir des explications claires et détaillées
        
        Réponds toujours en français et de manière naturelle."""}
    ]

# Titre de l'application
st.title("💬 Assistant Conversationnel Intelligent")

# Zone de texte pour la saisie de l'utilisateur
user_input = st.text_input("Posez votre question ou partagez vos pensées :", key="user_input")

# Bouton pour envoyer le message
if st.button("Envoyer") or user_input:
    if user_input:
        # Ajout du message de l'utilisateur à l'historique
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        try:
            # Obtention de la réponse de ChatGPT
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=st.session_state.messages,
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
st.subheader("Conversation :")
for message in st.session_state.messages[1:]:  # Skip the system message
    if message["role"] == "user":
        st.write("👤 Vous :")
        st.write(message["content"])
    else:
        st.write("🤖 Assistant :")
        st.write(message["content"])
    st.write("---")
