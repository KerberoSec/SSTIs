import os
import sqlite3
import hashlib
import secrets
from flask import Flask, render_template_string, request, redirect, url_for, session, g
from jinja2 import Environment
from jinja2.sandbox import SandboxedEnvironment

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
DATABASE = '/tmp/museum.db'

# Simulated shell transcripts
SIMULATED_SHELLS = {
    'template': """
SIMULATED TEMPLATE SHELL - No Real System Access
This is a transcript showing simulated template shell behavior.
All commands are simulated and do not execute on the real system.

>>> {% for key in config %}
...   {{ key }}
... {% endfor %}
[Simulated output - no real data accessed]

>>> {{ ''.__class__.__mro__[1].__subclasses__() }}
[Simulated - sandbox blocked access to dangerous attributes]
""",
    'os': """
SIMULATED OS SHELL - No Real System Access
This is a transcript showing simulated OS command execution.
All commands are simulated and do not execute on the real system.

$ ls -la
[Simulated directory listing - no real files accessed]

$ cat /etc/passwd
[Simulated - file access blocked by sandbox]

$ whoami
[Simulated - no real process execution]

Note: This is a controlled environment for demonstrating SSTI vulnerabilities
without actual system compromise.
"""
}

# Museum metadata - available as whitelisted helper
MUSEUM_META = {
    'name': 'The Template Museum',
    'founded': '2024',
    'collection_size': 137,
    'type': 'Digital Art Gallery'
}

def get_db():
    """Get database connection."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize the database."""
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            flag TEXT UNIQUE NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def hash_password(password):
    """Hash a password."""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_flag(username):
    """Generate a unique flag for a user."""
    random_part = secrets.token_hex(16)
    return f"FLAG{{{username}_{random_part}}}"

# Whitelisted helper functions for sandbox
def get_museum_meta(key=None):
    """Get museum metadata - whitelisted helper."""
    if key:
        return MUSEUM_META.get(key, 'Unknown')
    return MUSEUM_META

def get_curator_note():
    """Get curator's note - whitelisted helper."""
    return "Welcome to our digital collection! This museum showcases the finest templates."

# Custom sandboxed environment with only whitelisted helpers
class RestrictedSandbox(SandboxedEnvironment):
    """Highly restricted sandbox environment."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only allow specific whitelisted helpers
        self.globals = {
            'get_museum_meta': get_museum_meta,
            'get_curator_note': get_curator_note,
        }
        # Add safe built-in filters
        self.filters.update({
            'escape': self.filters['escape'],
            'upper': self.filters['upper'],
        })
    
    def is_safe_attribute(self, obj, attr, value):
        """Block access to dangerous attributes."""
        # Block all attribute access except for very basic operations
        dangerous_attrs = [
            '__class__', '__mro__', '__subclasses__', '__globals__',
            '__code__', '__closure__', '__func__', '__self__',
            '__dict__', '__module__', '__builtins__', 'func_globals',
            'gi_frame', 'gi_code', 'cr_frame', 'cr_code'
        ]
        if attr.startswith('_') or attr in dangerous_attrs:
            return False
        return True

sandbox = RestrictedSandbox()

@app.route('/')
def index():
    """Home page."""
    if 'user_id' in session:
        return redirect(url_for('preview'))
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Template Museum - Login</title></head>
    <body>
        <h1>Welcome to the Template Museum</h1>
        <p><a href="/register">Register</a> | <a href="/login">Login</a></p>
        <p><a href="/simulated-shells">View Simulated Shell Transcripts</a></p>
    </body>
    </html>
    '''

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        display_name = request.form.get('display_name', '').strip()
        
        if not username or not password or not display_name:
            return 'All fields are required!', 400
        
        db = get_db()
        cursor = db.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return 'Username already exists!', 400
        
        # Create user with unique flag
        password_hash = hash_password(password)
        flag = generate_flag(username)
        
        try:
            cursor.execute(
                'INSERT INTO users (username, password_hash, display_name, flag) VALUES (?, ?, ?, ?)',
                (username, password_hash, display_name, flag)
            )
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return 'Error creating user', 500
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Register - Template Museum</title></head>
    <body>
        <h1>Register</h1>
        <form method="POST">
            <label>Username: <input type="text" name="username" required></label><br>
            <label>Password: <input type="password" name="password" required></label><br>
            <label>Display Name: <input type="text" name="display_name" required></label><br>
            <button type="submit">Register</button>
        </form>
        <p><a href="/">Back to Home</a></p>
    </body>
    </html>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return 'Username and password are required!', 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute(
            'SELECT id, password_hash FROM users WHERE username = ?',
            (username,)
        )
        user = cursor.fetchone()
        
        if user and user['password_hash'] == hash_password(password):
            session['user_id'] = user['id']
            return redirect(url_for('preview'))
        
        return 'Invalid credentials!', 401
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Login - Template Museum</title></head>
    <body>
        <h1>Login</h1>
        <form method="POST">
            <label>Username: <input type="text" name="username" required></label><br>
            <label>Password: <input type="password" name="password" required></label><br>
            <button type="submit">Login</button>
        </form>
        <p><a href="/">Back to Home</a></p>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    """User logout."""
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/preview')
def preview():
    """Preview page with SSTI vulnerability via display_name."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        'SELECT username, display_name, flag FROM users WHERE id = ?',
        (session['user_id'],)
    )
    user = cursor.fetchone()
    
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login'))
    
    # SSTI vulnerability: display_name is rendered as a template
    # But using sandboxed environment with limited helpers
    template_string = f'''
    <!DOCTYPE html>
    <html>
    <head><title>Museum Preview</title></head>
    <body>
        <h1>Welcome to Your Preview, {user['display_name']}!</h1>
        <p>Your flag: {user['flag']}</p>
        <p>Museum: {{{{ get_museum_meta('name') }}}}</p>
        <p>Curator's Note: {{{{ get_curator_note() }}}}</p>
        <p><a href="/logout">Logout</a></p>
    </body>
    </html>
    '''
    
    try:
        # Render with sandboxed environment
        template = sandbox.from_string(template_string)
        return template.render()
    except Exception as e:
        return f'Template rendering error: {str(e)}', 500

@app.route('/simulated-shells')
def simulated_shells():
    """Show simulated shell transcripts."""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simulated Shell Transcripts</title>
        <style>
            pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; }}
            .warning {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Simulated Shell Transcripts</h1>
        <p class="warning">⚠️ IMPORTANT: These are SIMULATED transcripts for educational purposes.</p>
        <p class="warning">No actual system commands are executed. No real files, processes, or network connections are created.</p>
        
        <h2>Template Shell (Simulated)</h2>
        <pre>{SIMULATED_SHELLS['template']}</pre>
        
        <h2>OS Shell (Simulated)</h2>
        <pre>{SIMULATED_SHELLS['os']}</pre>
        
        <p><a href="/">Back to Home</a></p>
    </body>
    </html>
    '''

if __name__ == '__main__':
    init_db()
    # Run on 0.0.0.0 for Docker, but will be isolated by network config
    app.run(host='0.0.0.0', port=5000, debug=False)
