import pandas as pd
import streamlit as st
import openai
from datetime import datetime

# Configuration de OpenAI avec la clé API depuis Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Chatbot Articles Médias",
    page_icon="📰",
    layout="wide"
)

# URL du fichier Excel (à remplacer par votre lien de partage)
EXCEL_URL = "https://docs.google.com/spreadsheets/d/1your_file_id/export?format=xlsx"

# Fonction pour charger et préparer les données
@st.cache_data
def load_data():
    try:
        # Essayer d'abord de charger depuis le fichier local
        df = pd.read_excel("data/articles_medias_small.xlsx")
    except Exception as e:
        st.error(f"""
        Pour utiliser ce chatbot, vous devez :
        1. Créer un fichier Excel nommé 'articles_medias_small.xlsx'
        2. Le placer dans un dossier 'data' à la racine du projet
        3. Le fichier doit contenir les colonnes : 'Date', 'Titre', 'Contenu'
        
        Erreur détaillée : {str(e)}
        """)
        return None
    
    # Conversion de la colonne Date en datetime
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df.sort_values('Date', ascending=True)

# Fonction pour trouver les articles pertinents avec filtrage par date
def find_relevant_articles(query, df, start_date=None, end_date=None):
    if df is None:
        return []
        
    query = query.lower()
    scores = []
    
    # Filtrer par date si spécifié
    if start_date:
        df = df[df['Date'] >= start_date]
    if end_date:
        df = df[df['Date'] <= end_date]
    
    for idx, row in df.iterrows():
        content = str(row.get('Contenu', '')).lower()
        title = str(row.get('Titre', '')).lower()
        
        # Score basé sur la présence des mots dans le titre (poids plus élevé) et le contenu
        title_score = sum(word in title for word in query.split()) * 2
        content_score = sum(word in content for word in query.split())
        total_score = title_score + content_score
        
        if total_score > 0:
            scores.append((idx, total_score, row['Date']))
    
    # Trier par score puis par date
    scores.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [(df.loc[idx], score) for idx, score, _ in scores]

def generate_chronological_synthesis(articles):
    if not articles:
        return "Aucun article pertinent trouvé."
    
    # Trier les articles par date
    sorted_articles = sorted(articles, key=lambda x: x[0]['Date'])
    
    context = """Fais une synthèse chronologique détaillée des articles suivants. 
    Pour chaque période importante :
    1. Indique clairement la date
    2. Résume les événements marquants
    3. Mets en évidence l'évolution du sujet dans le temps
    4. Termine par une conclusion sur l'évolution globale du sujet

    Articles à synthétiser :\n\n"""
    
    for article, score in sorted_articles:
        context += f"Date: {article['Date'].strftime('%d/%m/%Y')}\n"
        context += f"Titre: {article.get('Titre', 'Non disponible')}\n"
        context += f"Contenu: {article.get('Contenu', 'Non disponible')}\n\n"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en analyse d'articles d'actualité. Tu dois produire des synthèses chronologiques détaillées en français, en mettant en évidence l'évolution des événements dans le temps."},
                {"role": "user", "content": context}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].message['content']
    except Exception as e:
        return f"Erreur lors de la génération de la synthèse : {str(e)}"

def generate_synthesis(articles):
    if not articles:
        return "Aucun article pertinent trouvé."
        
    context = "Voici plusieurs articles d'actualité. Fais-en une synthèse claire et concise en français :\n\n"
    for article, score in articles:
        context += f"Article (pertinence {score:.2%}):\n"
        context += f"Titre: {article.get('Titre', 'Non disponible')}\n"
        context += f"Contenu: {article.get('Contenu', 'Non disponible')}\n\n"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en analyse d'articles d'actualité. Tu dois produire des synthèses claires, objectives et bien structurées en français."},
                {"role": "user", "content": context}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message['content']
    except Exception as e:
        return f"Erreur lors de la génération de la synthèse : {str(e)}"

def main():
    st.title("💬 Assistant Articles Médias Intelligent")
    
    # Chargement des données
    df = load_data()
    if df is None:
        return

    # Interface utilisateur
    st.write("---")
    
    # Sélection du mode de recherche
    search_mode = st.radio(
        "Mode de recherche :",
        ["Synthèse thématique chronologique", "Résumé détaillé d'un sujet"]
    )
    
    # Filtres de date
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Date de début", min(df['Date'].dt.date))
    with col2:
        end_date = st.date_input("Date de fin", max(df['Date'].dt.date))

    # Zone de recherche
    user_input = st.text_input(
        "Quel sujet vous intéresse ?",
        placeholder="Ex: énergies renouvelables, économie, sport..."
    )
    
    if user_input:
        # Conversion des dates
        start_date = pd.Timestamp(start_date)
        end_date = pd.Timestamp(end_date)
        
        # Recherche des articles
        relevant_articles = find_relevant_articles(user_input, df, start_date, end_date)
        
        if relevant_articles:
            # Génération de la synthèse selon le mode choisi
            if search_mode == "Synthèse thématique chronologique":
                synthesis = generate_chronological_synthesis(relevant_articles)
            else:
                synthesis = generate_synthesis(relevant_articles)
            
            # Affichage de la synthèse
            st.write("---")
            st.subheader("Synthèse :")
            st.write(synthesis)
            
            # Affichage des articles sources
            st.write("---")
            st.subheader("Articles sources :")
            for article, score in sorted(relevant_articles, key=lambda x: x[0]['Date'], reverse=True):
                with st.expander(f"📰 {article['Date'].strftime('%d/%m/%Y')} - {article.get('Titre', 'Sans titre')}"):
                    st.markdown(f"""
                    **Score de pertinence**: {score:.2%}
                    
                    **Contenu**: {article.get('Contenu', 'Non disponible')}
                    """)
        else:
            st.warning("Aucun article trouvé pour cette recherche sur la période spécifiée.")

if __name__ == "__main__":
    main()
