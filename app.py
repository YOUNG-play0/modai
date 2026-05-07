from flask import Flask, request, jsonify, send_from_directory
from groq import Groq
from functools import wraps
import psycopg2
import psycopg2.extras
import bcrypt
import os
import jwt
import datetime

app = Flask(__name__, static_folder='.')

SECRET_KEY = os.environ.get("SECRET_KEY", "modai-secret-key-2024")
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
    today = datetime.date.today()
    last = user['last_reset']
    if isinstance(last, str):
        last = datetime.datetime.strptime(last, '%Y-%m-%d').date()
    if last < today:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE users SET daily_count=0, last_reset=%s WHERE email=%s", (today, user['email']))
        conn.commit()
        cur.close()
        conn.close()
        user['daily_count'] = 0
    return user

def create_token(email):
    payload = {
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['email']
    except:
        return None

def get_token_from_request():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:]
    return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({'erreur': 'Non connecte', 'redirect': '/login'}), 401
        email = verify_token(token)
        if not email:
            return jsonify({'erreur': 'Token invalide', 'redirect': '/login'}), 401
        request.user_email = email
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

AUTH_HTML = """<!DOCTYPE html>
<!-- v2 -->
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MODAI — Connexion</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --gold: #C9A84C;
  --gold-light: #E8C97A;
  --black: #080808;
  --dark: #0F0F0F;
  --card: #141414;
  --border: #222;
  --text: #E8E2D9;
  --muted: #6A6058;
}
body {
  background: var(--black);
  color: var(--text);
  font-family: 'DM Mono', monospace;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.logo {
  font-family: 'Cormorant Garamond', serif;
  font-size: 32px;
  font-weight: 300;
  letter-spacing: 8px;
  color: var(--gold);
  margin-bottom: 48px;
}
.logo span { color: var(--text); font-weight: 600; }
.auth-card {
  background: var(--card);
  border: 1px solid var(--border);
  padding: 48px;
  width: 100%;
  max-width: 420px;
}
.auth-tabs {
  display: flex;
  margin-bottom: 36px;
  border-bottom: 1px solid var(--border);
}
.auth-tab {
  flex: 1;
  padding: 12px;
  text-align: center;
  cursor: pointer;
  font-size: 11px;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--muted);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.2s;
}
.auth-tab.active { color: var(--gold); border-bottom-color: var(--gold); }
.form-group { margin-bottom: 20px; }
label {
  display: block;
  font-size: 10px;
  letter-spacing: 2px;
  color: var(--muted);
  text-transform: uppercase;
  margin-bottom: 8px;
}
input {
  width: 100%;
  background: var(--dark);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 12px 16px;
  font-family: 'DM Mono', monospace;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}
input:focus { border-color: var(--gold); }
.btn-auth {
  width: 100%;
  background: var(--gold);
  color: var(--black);
  border: none;
  padding: 14px;
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  letter-spacing: 3px;
  text-transform: uppercase;
  cursor: pointer;
  margin-top: 8px;
  transition: all 0.2s;
}
.btn-auth:hover { background: var(--gold-light); }
.btn-auth:disabled { opacity: 0.5; cursor: not-allowed; }
.error-msg {
  background: rgba(255,80,80,0.1);
  border: 1px solid rgba(255,80,80,0.3);
  color: #ff6060;
  padding: 10px 14px;
  font-size: 12px;
  margin-bottom: 16px;
  display: none;
}
.success-msg {
  background: rgba(201,168,76,0.1);
  border: 1px solid var(--gold);
  color: var(--gold);
  padding: 10px 14px;
  font-size: 12px;
  margin-bottom: 16px;
  display: none;
}
.divider {
  width: 40px;
  height: 1px;
  background: var(--gold);
  margin: 24px auto;
}
.back-link {
  text-align: center;
  margin-top: 24px;
  font-size: 11px;
  color: var(--muted);
}
.back-link a {
  color: var(--gold);
  text-decoration: none;
}
.plan-info {
  background: var(--dark);
  border: 1px solid var(--border);
  padding: 16px;
  margin-bottom: 24px;
  font-size: 11px;
  line-height: 1.8;
  color: var(--muted);
}
.plan-info strong { color: var(--gold); }
</style>
</head>
<body>

<div class="logo">MOD<span>AI</span></div>

<div class="auth-card">
  <div class="auth-tabs">
    <div class="auth-tab active" id="tab-login" onclick="switchTab('login')">Connexion</div>
    <div class="auth-tab" id="tab-signup" onclick="switchTab('signup')">Inscription</div>
  </div>

  <div class="plan-info">
    <strong>Plan Gratuit :</strong> 5 générations/jour<br>
    <strong>Plan Pro (19€/mois) :</strong> Illimité + toutes plateformes
  </div>

  <div class="error-msg" id="errorMsg"></div>
  <div class="success-msg" id="successMsg"></div>

  <!-- LOGIN FORM -->
  <div id="form-login">
    <div class="form-group">
      <label>Email</label>
      <input type="email" id="login-email" placeholder="votre@email.com">
    </div>
    <div class="form-group">
      <label>Mot de passe</label>
      <input type="password" id="login-password" placeholder="••••••••" onkeydown="if(event.key==='Enter')doLogin()">
    </div>
    <button class="btn-auth" id="btn-login" onclick="doLogin()">Se connecter</button>
  </div>

  <!-- SIGNUP FORM -->
  <div id="form-signup" style="display:none">
    <div class="form-group">
      <label>Email</label>
      <input type="email" id="signup-email" placeholder="votre@email.com">
    </div>
    <div class="form-group">
      <label>Mot de passe</label>
      <input type="password" id="signup-password" placeholder="Minimum 6 caractères" onkeydown="if(event.key==='Enter')doSignup()">
    </div>
    <button class="btn-auth" id="btn-signup" onclick="doSignup()">Créer mon compte</button>
  </div>

</div>

<div class="back-link">
  <a href="/landing">← Retour à l'accueil</a>
</div>

<script>
// Check URL to show correct tab
if (window.location.pathname === '/signup') switchTab('signup');

function switchTab(tab) {
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-signup').classList.toggle('active', tab === 'signup');
  document.getElementById('form-login').style.display = tab === 'login' ? 'block' : 'none';
  document.getElementById('form-signup').style.display = tab === 'signup' ? 'block' : 'none';
  hideMessages();
}

function showError(msg) {
  const el = document.getElementById('errorMsg');
  el.textContent = msg;
  el.style.display = 'block';
  document.getElementById('successMsg').style.display = 'none';
}

function showSuccess(msg) {
  const el = document.getElementById('successMsg');
  el.textContent = msg;
  el.style.display = 'block';
  document.getElementById('errorMsg').style.display = 'none';
}

function hideMessages() {
  document.getElementById('errorMsg').style.display = 'none';
  document.getElementById('successMsg').style.display = 'none';
}

async function doLogin() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const btn = document.getElementById('btn-login');

  if (!email || !password) { showError('Remplissez tous les champs.'); return; }

  btn.disabled = true;
  btn.textContent = 'Connexion...';

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (data.success) {
      localStorage.setItem('modai_token', data.token);
      showSuccess('Connecté ! Redirection...');
      setTimeout(() => window.location.href = '/', 1000);
    } else {
      showError(data.erreur || 'Erreur de connexion.');
    }
  } catch {
    showError('Erreur serveur. Réessayez.');
  }

  btn.disabled = false;
  btn.textContent = 'Se connecter';
}

async function doSignup() {
  const email = document.getElementById('signup-email').value.trim();
  const password = document.getElementById('signup-password').value;
  const btn = document.getElementById('btn-signup');

  if (!email || !password) { showError('Remplissez tous les champs.'); return; }
  if (password.length < 6) { showError('Mot de passe trop court (6 caractères minimum).'); return; }

  btn.disabled = true;
  btn.textContent = 'Création...';

  try {
    const res = await fetch('/api/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (data.success) {
      localStorage.setItem('modai_token', data.token);
      showSuccess('Compte créé ! Redirection...');
      setTimeout(() => window.location.href = '/', 1000);
    } else {
      showError(data.erreur || 'Erreur création compte.');
    }
  } catch {
    showError('Erreur serveur. Réessayez.');
  }

  btn.disabled = false;
  btn.textContent = 'Créer mon compte';
}
</script>
</body>
</html>
"""

@app.route('/login')
def login_page():
    return AUTH_HTML, 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/signup')
def signup_page():
    return AUTH_HTML, 200, {'Content-Type': 'text/html; charset=utf-8'}

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
    token = create_token(email)
    return jsonify({'success': True, 'email': email, 'plan': 'free', 'token': token})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    user = get_user(email)
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({'erreur': 'Email ou mot de passe incorrect'}), 401
    token = create_token(email)
    return jsonify({'success': True, 'email': email, 'plan': user['plan'], 'token': token})

@app.route('/api/me', methods=['GET'])
def me():
    token = get_token_from_request()
    if not token:
        return jsonify({'connecte': False})
    email = verify_token(token)
    if not email:
        return jsonify({'connecte': False})
    user = get_user(email)
    if not user:
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
    user = get_user(request.user_email)
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
    email = request.user_email
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
        else:
            hashed = bcrypt.hashpw(sale_id.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute("""
                INSERT INTO users (email, password, plan, gumroad_id)
                VALUES (%s, %s, 'pro', %s)
                ON CONFLICT (email) DO UPDATE SET plan='pro', gumroad_id=%s
            """, (email, hashed, sale_id, sale_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

if __name__ == '__main__':
    print("MODAI V3 JWT - http://localhost:5000")
    app.run(debug=True, port=5000)
