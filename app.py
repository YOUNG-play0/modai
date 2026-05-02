from flask import Flask, request, jsonify, send_from_directory
from groq import Groq
import os

app = Flask(__name__, static_folder='.')
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

chat_history = []

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/landing')
def landing():
    return send_from_directory('.', 'landing.html')

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
                {"role": "system", "content": "Tu es un expert en marketing mode et e-commerce."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.8
        )
        return jsonify({'contenu': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    if not message:
        return jsonify({'erreur': 'Message manquant'}), 400
    chat_history.append({"role": "user", "content": message})
    recent_history = chat_history[-10:]
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es un assistant specialise en mode e-commerce. Reponds en francais, sois pratique et concis."}
            ] + recent_history,
            max_tokens=800,
            temperature=0.7
        )
        reponse = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": reponse})
        return jsonify({'reponse': reponse})
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
