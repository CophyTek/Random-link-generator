from flask import Flask, request, render_template, redirect, url_for, jsonify, session
import os
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['SECRET_KEY'] = 'your_secret_key'
purchase_amount = 10
purchase_made = False  # Define purchase_made as a global variable

# Initialize database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS balance
                 (id INTEGER PRIMARY KEY,
                  amount REAL NOT NULL DEFAULT 0.0)''')
    c.execute("INSERT OR IGNORE INTO balance (id, amount) VALUES (1, 1000.0)")
    conn.commit()
    conn.close()

# Initialize the database
init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT amount FROM balance WHERE id = 1")
    balance = c.fetchone()[0]
    conn.close()
    return render_template('index.html', balance=balance)

@app.route('/upload_screenshot', methods=['POST'])
def upload_screenshot():
    global purchase_made
    if 'screenshot' not in request.files:
        return redirect(request.url)
    file = request.files['screenshot']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("UPDATE balance SET amount = amount + ? WHERE id = 1", (purchase_amount * 1.5,))
        c.execute("SELECT amount FROM balance WHERE id = 1")
        balance = c.fetchone()[0]
        conn.commit()
        conn.close()
        purchase_made = False
        return jsonify({'message': 'Screenshot uploaded successfully!', 'new_balance': balance})
    return 'File not allowed.'

@app.route('/purchase_link', methods=['POST'])
def purchase_link():
    global purchase_made
    if purchase_made:
        return jsonify({'message': 'You have already purchased a link. Please upload a screenshot before purchasing again.'}), 400
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT amount FROM balance WHERE id = 1")
    balance = c.fetchone()[0]
    if balance >= purchase_amount:
        c.execute("UPDATE balance SET amount = amount - ? WHERE id = 1", (purchase_amount,))
        c.execute("SELECT amount FROM balance WHERE id = 1")
        balance = c.fetchone()[0]
        conn.commit()
        conn.close()
        purchase_made = True
        return jsonify({'message': 'Link purchased successfully!', 'new_balance': balance})
    conn.close()
    return jsonify({'message': 'Insufficient balance to purchase a link.'}), 400

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return jsonify({'message': 'Username already exists.'}), 400
    
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Registration successful!'})

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if not user or not check_password_hash(user[2], password):
        return jsonify({'message': 'Invalid username or password.'}), 400
    
    session['username'] = username
    return jsonify({'message': 'Login successful!'})

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
