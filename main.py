from flask import Flask, render_template, request, redirect, url_for, flash
import pymysql
app = Flask(__name__)
app.secret_key='votre_cle_secrete'
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="Nounou@1206",
        db="distributeur_db",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
@app.route('/')
def index():
    return redirect('/login')
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')
@app.route('/authentification', methods=['POST'])
def authentificate():
    email = request.form.get('email')
    password = request.form.get('password')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM utilisateurs WHERE email = %s AND password = %s",
            (email, password)
        )
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if user:
        return redirect(url_for('dashboard'))
    else:
        flash( "Email ou mot de passe incorrect!")
        return redirect(url_for('login_page'))
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')
if __name__ == "__main__":
    app.run(debug=True)
        


