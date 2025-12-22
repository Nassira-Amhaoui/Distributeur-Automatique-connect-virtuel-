from flask import Flask, render_template, request, redirect, url_for, flash
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
app = Flask(__name__)
app.secret_key='votre_cle_secrete'
serializer= URLSafeTimedSerializer(app.secret_key)
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
@app.route('/forget_password', methods=['GET', 'post'])
def forget_password():
    reset_link = None
    if request.method == 'POST':
        email = request.form.get('email')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM utilisateurs WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()
        if not user:
            flash("Cet email n'existe pas")
        else:
            token = serializer.dumps(email, salt='reset-password')
            reset_link = url_for('reset_password', token=token, _external=True)
            flash("Un lien de réinitialisation du mot de passe a été envoyé à votre adresse email.")
    return render_template('forget_password.html', reset_link=reset_link)
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='reset-password', max_age=900)
    except:
        flash("Le lien est invalide ou a expiré.")
        return redirect(url_for('login_page'))
    if request.method == 'POST':
        password= request.form.get('password')
        confirm_password= request.form.get('confirm_password')
        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas")
            return redirect(url_for('reset_password', token=token))
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE utilisateurs SET password = %s WHERE email = %s",(hashed_password, email))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Mot de passe modifié avec succès!")
        return redirect(url_for('login_page'))
    return render_template('reset_password.html', email=email)
@app.route('/authentification', methods=['POST'])
def authentificate():
    email = request.form.get('email')
    password = request.form.get('password')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM utilisateurs WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    if user and check_password_hash(user['password'], password):
        return redirect(url_for('dashboard'))
    else:
        flash( "Email ou mot de passe incorrect!")
        return redirect(url_for('login_page'))
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')
if __name__ == "__main__":
    app.run(debug=True)
        


