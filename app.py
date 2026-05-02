from flask import Flask, request, jsonify, send_from_directory
from groq import Groq
import os

app = Flask(__name__, static_folder='.')
client = Groq(api_key=os.environ.get("GROQ_API_KEY", "METS_TA_CLE_ICI"))

# Système de chat - mémoire de la conversation
chat_history = []

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/generer', methods=['POST'])
def generer():
    data = request.get_json()
    prompt = data.get('prompt', '')

    if not prompt:
        return jsonify({'erreur': 'Prompt manquant'}), 400

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un expert en marketing mode et e-commerce. Tu génères du contenu professionnel, engageant et adapté à chaque plateforme."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.8
        )
        contenu = response.choices[0].message.content
        return jsonify({'contenu': contenu})

    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')

    if not message:
        return jsonify({'erreur': 'Message manquant'}), 400

    # Ajouter le message utilisateur à l'historique
    chat_history.append({"role": "user", "content": message})

    # Garder seulement les 10 derniers messages (pour éviter de dépasser le contexte)
    recent_history = chat_history[-10:]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """Tu es un assistant spécialisé en mode e-commerce et marketing digital pour les boutiques en ligne. 
Tu aides les propriétaires de boutiques mode à :
- Améliorer leurs descriptions produits et leur contenu marketing
- Développer leur présence sur les réseaux sociaux (Instagram, TikTok, Facebook)
- Comprendre les tendances mode et les stratégies de vente
- Répondre aux clients et gérer leur e-réputation
- Augmenter leurs ventes en ligne

Réponds en français, sois pratique, concis et donne des conseils actionnables. 
Utilise parfois des emojis pour être plus engageant. Sois chaleureux et professionnel."""
                }
            ] + recent_history,
            max_tokens=800,
            temperature=0.7
        )

        reponse = response.choices[0].message.content

        # Ajouter la réponse à l'historique
        chat_history.append({"role": "assistant", "content": reponse})

        return jsonify({'reponse': reponse})

    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


if __name__ == '__main__':
    print("🚀 MODAI V2 démarré sur http://localhost:5000")
    app.run(debug=True, port=5000)
    
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')
@app.route('/landing')
def landing():
    return send_from_directory('.', 'landing.html')
