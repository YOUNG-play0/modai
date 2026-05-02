from flask import Flask, request, jsonify, send_from_directory
import anthropic
import os

app = Flask(__name__, static_folder='.')

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/generer', methods=['POST'])
def generer():
    data = request.json
    nom = data.get('nom', '')
    prix = data.get('prix', '')
    couleur = data.get('couleur', '')
    matiere = data.get('matiere', '')
    details = data.get('details', '')

    prompt = f"""Tu es un expert en copywriting pour boutiques de mode en ligne.

Génère du contenu marketing pour ce produit :
- Nom : {nom}
- Prix : {prix if prix else 'Non précisé'}
- Couleur : {couleur if couleur else 'Non précisée'}
- Matière : {matiere if matiere else 'Non précisée'}
- Détails : {details if details else 'Aucun'}

Réponds UNIQUEMENT dans ce format exact, sans rien ajouter avant ou après :

DESCRIPTION_PRODUIT:
[Écris une description produit de 80-100 mots, convaincante, orientée bénéfices client, optimisée SEO. Ton professionnel et élégant.]

POST_INSTAGRAM:
[Écris un post Instagram engageant de 60-80 mots avec 2-3 emojis pertinents et 8-10 hashtags mode populaires en fin de post.]"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    contenu = message.content[0].text

    # Parser la réponse
    description = ""
    instagram = ""

    if "DESCRIPTION_PRODUIT:" in contenu and "POST_INSTAGRAM:" in contenu:
        parties = contenu.split("POST_INSTAGRAM:")
        description = parties[0].replace("DESCRIPTION_PRODUIT:", "").strip()
        instagram = parties[1].strip()
    else:
        description = contenu
        instagram = "Erreur de génération. Réessaie."

    return jsonify({
        "description": description,
        "instagram": instagram
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
