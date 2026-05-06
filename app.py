from flask import Flask, request, jsonify, send_from_directory, session
from groq import Groq
from functools import wraps
import psycopg2
import psycopg2.extras
import bcrypt
import os
from datetime import datetime, date

app = Flask(__name__, static_folder='.')
app.secret_key = os.environ.get("SECRET_KEY", "modai-secret-key-2024")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:oVvd5ZovMp7ZkFj2@db.lbkeettjmqiqitnxalwr.supabase.co:5432/postgres")

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            plan VARCHAR(20) DEFAULT 'free',
            daily_count INTEGER DEFAULT 0,
            last_reset DATE DEFAULT CURRENT_DATE,
            gumroad_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()
    print("DB ready")

try:
    init_db()
except Exception as e:
    print(f"DB error: {e}")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_user(email):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def reset_daily_if_needed(user):
    today = date.today()
    last = user['last_reset']
    if isinstance(last, str):
        last = datetime.strptime(last, '%Y-%m-%d').date()
    if last < today:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE users SET daily_count=0, last_reset=%s WHERE email=%s", (today, user['email']))
        conn.commit()
        cur.close()
        conn.close()
        user['daily_count'] = 0
    return user

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_email' not in session:
            return jsonify({'erreur': 'Non connecte', 'redirect': '/login'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/terms')
def terms():
    return send_from_directory('.', 'templatesterms.html')

@app.route('/privacy')
def privacy():
    return send_from_directory('.', 'templatesprivacy.html')

@app.route('/refund')
def refund():
    return send_from_directory('.', 'templatesrefund.html')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/landing')
def landing():
    return send_from_directory('.', 'landing.html')

@app.route('/login')
def login_page():
    return send_from_directory('.', 'auth.html')

@app.route('/signup')
def signup_page():
    return send_from_directory('.', 'auth.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    if not email or not password:
        return jsonify({'erreur': 'Email et mot de passe requis'}), 400
    if len(password) < 6:
        return jsonify({'erreur': 'Mot de passe minimum 6 caracteres'}), 400
    if get_user(email):
        return jsonify({'erreur': 'Email deja utilise'}), 400
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500
    session['user_email'] = email
    return jsonify({'success': True, 'email': email, 'plan': 'free'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    user = get_user(email)
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({'erreur': 'Email ou mot de passe incorrect'}), 401
    session['user_email'] = email
    return jsonify({'success': True, 'email': email, 'plan': user['plan']})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/me', methods=['GET'])
def me():
    if 'user_email' not in session:
        return jsonify({'connecte': False})
    user = get_user(session['user_email'])
    if not user:
        session.clear()
        return jsonify({'connecte': False})
    user = reset_daily_if_needed(user)
    restantes = 5 - user['daily_count'] if user['plan'] == 'free' else 999
    return jsonify({
        'connecte': True,
        'email': user['email'],
        'plan': user['plan'],
        'daily_count': user['daily_count'],
        'generations_restantes': restantes
    })

@app.route('/api/generer', methods=['POST'])
@login_required
def generer():
    user = get_user(session['user_email'])
    user = reset_daily_if_needed(user)
    if user['plan'] == 'free' and user['daily_count'] >= 5:
        return jsonify({'erreur': 'Limite atteinte. Passez Pro !', 'upgrade': True}), 403
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
        contenu = response.choices[0].message.content
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE users SET daily_count=daily_count+1 WHERE email=%s", (user['email'],))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'contenu': contenu})
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

chat_history = {}

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    message = data.get('message', '')
    email = session['user_email']
    if not message:
        return jsonify({'erreur': 'Message manquant'}), 400
    if email not in chat_history:
        chat_history[email] = []
    chat_history[email].append({"role": "user", "content": message})
    recent = chat_history[email][-10:]
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es un assistant specialise en mode e-commerce. Reponds en francais, sois pratique et concis."}
            ] + recent,
            max_tokens=800,
            temperature=0.7
        )
        reponse = response.choices[0].message.content
        chat_history[email].append({"role": "assistant", "content": reponse})
        return jsonify({'reponse': reponse})
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

@app.route('/webhook/gumroad', methods=['POST'])
def gumroad_webhook():
    try:
        data = request.form.to_dict()
        email = data.get('email', '').lower().strip()
        sale_id = data.get('sale_id', '')
        refunded = data.get('refunded', 'false')
        if not email:
            return jsonify({'erreur': 'Email manquant'}), 400
        conn = get_db()
        cur = conn.cursor()
        if refunded == 'true':
            cur.execute("UPDATE users SET plan='free' WHERE email=%s", (email,))
            print(f"Downgraded: {email}")
        else:
            hashed = bcrypt.hashpw(sale_id.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute("""
                INSERT INTO users (email, password, plan, gumroad_id)
                VALUES (%s, %s, 'pro', %s)
                ON CONFLICT (email) DO UPDATE SET plan='pro', gumroad_id=%s
            """, (email, hashed, sale_id, sale_id))
            print(f"Upgraded Pro: {email}")
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

if __name__ == '__main__':
    print("MODAI V3 - http://localhost:5000")
    app.run(debug=True, port=5000)
