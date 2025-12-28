from flask import Flask, render_template, request, redirect, url_for, flash
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import secrets
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
        cursor.execute("UPDATE utilisateurs SET password = %s, reset_token = NULL WHERE email = %s",(hashed_password, email))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Mot de passe modifié avec succès!")
        return redirect(url_for('login_page'))
    return render_template('reset_password.html', email=email, token=token)
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
@app.route('/users')
def users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("select Id_User, UserName, email, role from utilisateurs")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('users.html', users=users)
@app.route('/produits')
def produits():
    return render_template('produits.html')
@app.route('/analytics')
def analytics():
    return render_template('analytics.html')
@app.route('/settings')
def settings():
    return render_template('settings.html')
@app.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        hashed_password = generate_password_hash('')
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
            "INSERT INTO utilisateurs (UserName, email, role, password) VALUES (%s, %s, %s, %s)",
            (username, email, role, hashed_password)
            )
            conn.commit()
        except pymysql.IntegrityError:
            conn.rollback()
            flash("Cet email est déjà utilisé.", "error")
            return redirect(url_for('add_user'))
        finally:
            cursor.close()
            conn.close()
        token = serializer.dumps(email, salt='reset-password')
        reset_link = url_for('reset_password', token=token, _external=True)
        flash(f"""Utilisateur ajouté avec succès!<br> <strong>Un lien de création de mot de passe a été envoyé:</strong><br>
              <a href="{reset_link}">{reset_link}</a>""", "success")
        return redirect(url_for('users'))
    return render_template('add_user.html')
@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        cursor.execute(
            "UPDATE utilisateurs SET UserName = %s, email = %s, role = %s WHERE Id_User = %s",
            (username, email, role, user_id)
        )
        conn.commit()
        flash("Utilisateur mis à jour avec succès!")
        return redirect(url_for('users'))
    else:
        cursor.execute("SELECT * FROM utilisateurs WHERE Id_User = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('edit_user.html', user=user)
@app.route('/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM utilisateurs WHERE Id_User = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Utilisateur supprimé avec succès!")
    return redirect(url_for('users'))
if __name__ == "__main__":
    app.run(debug=True)
        


