from flask import Flask, render_template, request, redirect, url_for, flash
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session
from translation import translations
import pymysql
app = Flask(__name__)
app.secret_key='votre_cle_secrete'
serializer= URLSafeTimedSerializer(app.secret_key)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à cette page.")
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à cette page.")
            return redirect(url_for('login_page'))
        if session.get('role') != 'admin':
            flash("Accès refusé. Vous n'avez pas les permissions nécessaires.")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_translator():
    def t(key):
        lang = session.get('language', 'fr')
        return translations.get(lang, {}).get(key, key)
    return dict(t=t)
# logout route
@app.route('/logout')
def logout():
    session.clear()
    flash("Vous avez été déconnecté avec succès.")
    return redirect(url_for('login_page'))
# Connection à la base de données
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
# login route
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')
# forgot password route
@app.route('/forget_password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = request.form.get('email')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM utilisateurs WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()
        cursor.close()
        if not user:
            flash("Cet email n'existe pas")
            return redirect(url_for('forget_password'))
        return redirect(url_for('reset_password'))
    return render_template('forget_password.html')
# reset password route
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        password= request.form.get('password')
        confirm_password= request.form.get('confirm_password')
        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas")
            return redirect(url_for('reset_password'))
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE utilisateurs SET password = %s WHERE Id_user = %s",(hashed_password, session.get('user_id')))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Mot de passe modifié avec succès!")
        return redirect(url_for('login_page'))
    return render_template('reset_password.html')
# authentification route
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
        session['user_id'] = user['Id_User']
        session['username'] = user['UserName']
        session['email'] = user['email']
        session['role'] = user['role']
        session['date_creation'] = user['Date_Creation']
        # Enrigistrer l'historique se connexions
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO login_history (user_id, date_login) VALUES (%s, NOW())", (user['Id_User'],))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
    else:
        flash( "Email ou mot de passe incorrect!")
        return redirect(url_for('login_page'))
# dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
# users management route
@app.route('/users')
@login_required
@admin_required
def users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("select Id_User, UserName, email, role from utilisateurs")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('users.html', users=users)
# products route
@app.route('/produits')
def produits():
    return render_template('produits.html')
# analytics route
@app.route('/analytics')
def analytics():
    return render_template('analytics.html')
# settings route

@app.route('/settings')
@login_required
def settings():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    last_logins = []
    role_stats = []
    total_users = 0

    if session.get('role') == 'admin':
        cursor.execute("""
            SELECT u.UserName, u.email, u.role, l.date_login
            FROM login_history l
            INNER JOIN utilisateurs u ON l.user_id = u.Id_User
            ORDER BY l.date_login DESC
            LIMIT 5
        """)
        last_logins = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS total_users FROM utilisateurs")
        total_users = cursor.fetchone()['total_users']

        cursor.execute("""
            SELECT role, COUNT(*) AS count
            FROM utilisateurs
            GROUP BY role
        """)
        role_stats = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'settings.html',
        last_logins=last_logins,
        role_stats=role_stats,
        total_users=total_users
    )
# update profile route
@app.route('/settings/update_profile', methods=['POST'])
@login_required
def update_profile():
    username = request.form.get('username')
    email = request.form.get('email')
    flash("Profil mis à jour avec succès", "success")
    return redirect(url_for('settings'))
# change password route
@app.route('/settings/change_password', methods=['POST'])
@login_required
def change_password():
    current = request.form.get('current_password')
    new = request.form.get('new_password')
    confirm = request.form.get('confirm_password')

    if not current or not new or not confirm:
        flash("Tous les champs sont obligatoires", "error")
        return redirect(url_for('settings'))

    if new != confirm:
        flash("Les mots de passe ne correspondent pas", "error")
        return redirect(url_for('settings'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT password FROM utilisateurs WHERE Id_User = %s",
        (session['user_id'],)
    )
    user = cursor.fetchone()

    if not user or not check_password_hash(user['password'], current):
        flash("Mot de passe actuel incorrect", "error")
        conn.close()
        return redirect(url_for('settings'))

    hashed = generate_password_hash(new)
    cursor.execute(
        "UPDATE utilisateurs SET password = %s WHERE Id_User = %s",
        (hashed, session['user_id'])
    )
    conn.commit()
    conn.close()

    flash("Mot de passe modifié avec succès", "success")
    return redirect(url_for('settings'))
# preferences route
@app.route('/settings/preferences', methods=['POST'])
@login_required
def update_preferences():
    language = request.form.get('language')
    theme = request.form.get('theme')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE utilisateurs SET language = %s, theme = %s WHERE Id_User = %s",
        (language, theme, session['user_id'])
    )
    conn.commit()
    conn.close()

    session['language'] = language 
    session['theme'] = theme

    flash("Préférences mises à jour avec succés", "success")
    return redirect(url_for('settings'))
# add user route
@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
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
# edit user route
@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
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
# delete user route
@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM utilisateurs WHERE Id_User = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Utilisateur supprimé avec succès!")
    return redirect(url_for('users'))
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT u.UserName, u.email, l.date_login, u.role
        FROM login_history l
        JOIN utilisateurs u ON l.user_id = u.Id_User
        ORDER BY l.date_login DESC
        LIMIT 5
    """)
    last_logins = cursor.fetchall()
    print(" DEBUG last_logins=", last_logins)
    cursor.execute("SELECT COUNT(*) as total_users FROM utilisateurs")
    total_users = cursor.fetchone()['total_users']

    cursor.execute("SELECT role, COUNT(*) as count FROM utilisateurs GROUP BY role")
    role_stats = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin.html', last_logins=last_logins,
                           total_users=total_users, role_stats=role_stats)
# lancer le serveur
if __name__ == "__main__":
    app.run(debug=True)
        


