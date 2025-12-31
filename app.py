from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
import os
from itsdangerous import URLSafeTimedSerializer
from functools import wraps


app = Flask(__name__)
load_dotenv()


app.secret_key = os.getenv('SECRET_KEY', 'votre_cle_secrete_par_defaut')

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='amhaouinassira8@gmail.com',
    MAIL_PASSWORD='yugu brdv qkrf mgwh',
    MAIL_DEFAULT_SENDER='amhaouinassira8@gmail.com'
)

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

def get_db_connection():
    """Établit une connexion à la base de données"""
    return mysql.connector.connect(
        host="localhost",
        user="Nassira Amhaoui",
        password="Nassira2005",
        database="gestion_stock"
    )


def login_required(f):
    """Décorateur pour protéger les routes nécessitant une connexion"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Décorateur pour protéger les routes administrateur uniquement"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            return redirect(url_for('login_page'))
        if session.get('role') != 'admin':
            flash("Accès refusé. Vous n'avez pas les permissions nécessaires.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def envoyer_email_admin(nom_produit, quantite):
    """Envoie un email d'alerte à l'administrateur"""
    try:
        msg = Message(
            subject="🚨 Alerte Stock – Produit épuisé",
            recipients=["amhaouinassira8@gmail.com"]
        )
        
        msg.body = f"""
Bonjour,

Le produit suivant nécessite une intervention :

Produit : {nom_produit}
Quantité restante : {quantite}

Merci de réapprovisionner le distributeur.

— Système Distributeur Automatique
        """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")
        return False

@app.context_processor
def inject_notifications():
    """Injecte les notifications et les infos utilisateur dans tous les templates"""
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT Id_Produit, Nom, Quantite, email_envoye
            FROM Produit
            WHERE Quantite < 2
        """)
        
        produits_faible = cursor.fetchall()

        for p in produits_faible:
            if p["Quantite"] <= 0 and not p["email_envoye"]:
                if envoyer_email_admin(p["Nom"], p["Quantite"]):
                    cursor.execute(
                        "UPDATE Produit SET email_envoye = 1 WHERE Id_Produit = %s",
                        (p["Id_Produit"],)
                    )
                    db.commit()

        
        current_user = None
        if 'user_id' in session:
            cursor.execute(
                "SELECT UserName, email, role FROM User WHERE Id_User = %s",
                (session['user_id'],)
            )
            current_user = cursor.fetchone()

        cursor.close()
        db.close()

        return dict(
            produits_faible=produits_faible,
            notif_count=len(produits_faible),
            current_user=current_user
        )
    except Exception as e:
        print(f"Erreur dans inject_notifications: {e}")
        return dict(produits_faible=[], notif_count=0, current_user=None)


@app.route('/')
def index():
    """Page d'accueil - redirige vers login"""
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET'])
def login_page():
    """Affiche la page de connexion"""
    return render_template('login.html')

@app.route('/authentification', methods=['POST'])
def authentificate():
    """Traite la connexion utilisateur"""
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['Id_User']
            session['username'] = user.get('UserName', 'Utilisateur')
            session['role'] = user.get('role', 'user')
            flash("Connexion réussie!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Email ou mot de passe incorrect!", "danger")
            return redirect(url_for('login_page'))
    except Exception as e:
        flash(f"Erreur lors de la connexion: {str(e)}", "danger")
        return redirect(url_for('login_page'))
    finally:
        cursor.close()
        conn.close()

@app.route('/logout')
@login_required
def logout():
    """Déconnexion de l'utilisateur"""
    session.clear()
    flash("Vous avez été déconnecté avec succès.", "info")
    return redirect(url_for('login_page'))

@app.route('/forget_password', methods=['GET', 'POST'])
def forget_password():
    """Page de récupération de mot de passe"""
    reset_link = None
    if request.method == 'POST':
        email = request.form.get('email')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM User WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if not user:
                flash("Cet email n'existe pas", "danger")
            else:
                token = serializer.dumps(email, salt='reset-password')
                reset_link = url_for('reset_password', token=token, _external=True)
                flash("Un lien de réinitialisation du mot de passe a été généré.", "success")
        except Exception as e:
            flash(f"Erreur: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()
    
    return render_template('forget_password.html', reset_link=reset_link)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Réinitialisation du mot de passe"""
    try:
        email = serializer.loads(token, salt='reset-password', max_age=900)
    except:
        flash("Le lien est invalide ou a expiré.", "danger")
        return redirect(url_for('login_page'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas", "danger")
            return redirect(url_for('reset_password', token=token))
        
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE User SET password = %s WHERE email = %s", 
                          (hashed_password, email))
            conn.commit()
            flash("Mot de passe modifié avec succès!", "success")
            return redirect(url_for('login_page'))
        except Exception as e:
            flash(f"Erreur: {str(e)}", "danger")
            return redirect(url_for('reset_password', token=token))
        finally:
            cursor.close()
            conn.close()
    
    return render_template('reset_password.html', email=email)


@app.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord principal"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Statistiques générales
        cursor.execute("SELECT COUNT(*) AS total FROM Produit")
        total_produits = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) AS total FROM Produit")
        total_distributeurs = cursor.fetchone()['total']
        
        cursor.execute("SELECT * FROM Produit WHERE Quantite <= 5 ORDER BY Quantite ASC")
        produits_faible = cursor.fetchall()
        
        # Revenus totaux
        cursor.execute("""
            SELECT SUM(h.Quantite * p.Prix) AS total
            FROM Historique h
            JOIN Produit p ON h.Id_Produit = p.Id_Produit
            WHERE h.Action = 'acheter'
        """)
        total_revenus = cursor.fetchone()['total'] or 0
        
        # Revenus du mois
        cursor.execute("""
            SELECT SUM(h.Quantite * p.Prix) AS total
            FROM Historique h
            JOIN Produit p ON h.Id_Produit = p.Id_Produit
            WHERE h.Action = 'acheter' 
            AND MONTH(h.Date_Action) = MONTH(CURDATE())
            AND YEAR(h.Date_Action) = YEAR(CURDATE())
        """)
        revenus_mois = cursor.fetchone()['total'] or 0
        
        # Top 5 ventes
        cursor.execute("""
            SELECT p.Nom, SUM(h.Quantite) AS total_ventes
            FROM Historique h
            JOIN Produit p ON h.Id_Produit = p.Id_Produit
            WHERE h.Action = 'acheter'
            GROUP BY h.Id_Produit
            ORDER BY total_ventes DESC
            LIMIT 5
        """)
        ventes = cursor.fetchall()
        
        # Stock produits
        cursor.execute("SELECT Nom, Quantite FROM Produit ORDER BY Quantite DESC")
        stock_produits = cursor.fetchall()
        
        # Ventes temporelles (7 derniers jours)
        cursor.execute("""
            SELECT DATE(h.Date_Action) as date, 
                   SUM(h.Quantite * p.Prix) AS revenus,
                   SUM(h.Quantite) AS quantite
            FROM Historique h
            JOIN Produit p ON h.Id_Produit = p.Id_Produit
            WHERE h.Action = 'acheter'
            AND h.Date_Action >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(h.Date_Action)
            ORDER BY date ASC
        """)
        ventes_temporelles = cursor.fetchall()
        
        # Produits populaires
        cursor.execute("""
            SELECT p.Nom, p.Prix, p.Quantite, 
                   COALESCE(SUM(h.Quantite), 0) AS total_ventes
            FROM Produit p
            LEFT JOIN Historique h ON p.Id_Produit = h.Id_Produit 
                AND h.Action = 'acheter'
            GROUP BY p.Id_Produit
            ORDER BY total_ventes DESC
            LIMIT 3
        """)
        produits_populaires = cursor.fetchall()
        
        # Données pour les graphiques
        dashboard_data = {
            'ventes': {
                'labels': [v['Nom'] for v in ventes],
                'data': [int(v['total_ventes'] or 0) for v in ventes]
            },
            'stock': {
                'labels': [p['Nom'] for p in stock_produits],
                'data': [p['Quantite'] for p in stock_produits]
            },
            'timeline': {
                'labels': [v['date'].strftime("%d/%m") for v in ventes_temporelles],
                'revenus': [float(v['revenus'] or 0) for v in ventes_temporelles],
                'quantites': [int(v['quantite'] or 0) for v in ventes_temporelles]
            }
        }

        return render_template(
            'dashboard.html',
            total_produits=total_produits,
            total_distributeurs=total_distributeurs,
            produits_faible=produits_faible,
            total_revenus=total_revenus,
            revenus_mois=revenus_mois,
            produits_populaires=produits_populaires,
            dashboard_data=dashboard_data,
            active="dashboard"
        )
    except Exception as e:
        flash(f"Erreur lors du chargement du dashboard: {str(e)}", "danger")
        return render_template('dashboard.html', active="dashboard")
    finally:
        cursor.close()
        conn.close()


@app.route('/produits')
@login_required
def produits():
    """Liste tous les produits"""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM produit")
        produits_list = cursor.fetchall()
        return render_template("produits.html", produits=produits_list, active="produits")
    except Exception as e:
        flash(f"Erreur: {str(e)}", "danger")
        return render_template("produits.html", produits=[], active="produits")
    finally:
        cursor.close()
        db.close()

@app.route('/ajouter_produit', methods=['POST'])
@login_required
def ajouter_produit():
    """Ajoute un nouveau produit"""
    nom = request.form.get('nom')
    etage = request.form.get('etage')
    quantite = request.form.get('quantite')

    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        cursor.execute("INSERT INTO produit (Nom, N_Etage, Quantite) VALUES (%s, %s, %s)",
                       (nom, etage, quantite))
        db.commit()
        flash("Produit ajouté avec succès!", "success")
    except Exception as e:
        flash(f"Erreur lors de l'ajout: {str(e)}", "danger")
    finally:
        cursor.close()
        db.close()
    
    return redirect(url_for('produits'))

@app.route("/modifier_produit", methods=["POST"])
@login_required
def modifier_produit():
    """Modifie un produit existant"""
    id_p = request.form.get("id")
    nom = request.form.get("nom")
    etage = request.form.get("etage")
    quantite = request.form.get("quantite")

    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        cursor.execute(
            "UPDATE produit SET Nom=%s, N_Etage=%s, Quantite=%s WHERE Id_Produit=%s",
            (nom, etage, quantite, id_p)
        )
        db.commit()
        flash("Produit modifié avec succès!", "success")
    except Exception as e:
        flash(f"Erreur lors de la modification: {str(e)}", "danger")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("produits"))

@app.route("/supprimer_produit", methods=["POST"])
@login_required
def supprimer_produit():
    """Supprime un produit"""
    id_p = request.form.get("id")

    db = get_db_connection()
    cursor = db.cursor()
    
    try:
        cursor.execute("DELETE FROM produit WHERE Id_Produit = %s", (id_p,))
        db.commit()
        flash("Produit supprimé avec succès!", "success")
    except Exception as e:
        flash(f"Erreur lors de la suppression: {str(e)}", "danger")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("produits"))

# ========== HISTORIQUE PRODUITS ==========
@app.route('/product_history')
@login_required
def product_history():
    """Affiche l'historique des produits"""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM Produit")
        produits = cursor.fetchall()

        cursor.execute("""
            SELECT h.Id_Historique, h.Action, h.Quantite, h.Date_Action, h.Id_Produit, p.Nom AS Produit
            FROM Historique h
            JOIN Produit p ON h.Id_Produit = p.Id_Produit
            ORDER BY h.Date_Action DESC
        """)
        all_history = cursor.fetchall()

        zoom = "month"
        historique_par_produit = defaultdict(list)

        for h in all_history:
            dt = h["Date_Action"]
            if zoom == "day":
                key = dt.strftime("%Y-%m-%d")
            elif zoom == "month":
                key = dt.strftime("%Y-%m")
            elif zoom == "hour":
                key = dt.strftime("%Y-%m-%d %H:00")
            else:
                key = dt.strftime("%Y-%m-%d")

            h["zoom_key"] = key
            pid = h["Id_Produit"]
            historique_par_produit[pid].append(h)
        
        historique_js = {}
        for pid, entries in historique_par_produit.items():
            entries_asc = sorted(entries, key=lambda x: x["Date_Action"])
            labels = []
            data_ajouter = []
            data_acheter = []

            for e in entries_asc:
                dt = e["Date_Action"]
                if isinstance(dt, datetime):
                    labels.append(dt.strftime("%d/%m/%Y %H:%M"))
                else:
                    labels.append(str(dt))

                if e["Action"] == "ajouter":
                    data_ajouter.append(e["Quantite"])
                    data_acheter.append(0)
                elif e["Action"] == "acheter":
                    data_acheter.append(e["Quantite"])
                    data_ajouter.append(0)
                else:
                    data_ajouter.append(0)
                    data_acheter.append(0)

            historique_js[pid] = {
                "labels": labels,
                "ajouter": data_ajouter,
                "acheter": data_acheter
            }

        return render_template(
            "product_history.html",
            produits=produits,
            historique=historique_par_produit,
            historique_js=historique_js,
            active="product_history"
        )
    except Exception as e:
        flash(f"Erreur: {str(e)}", "danger")
        return render_template("product_history.html", produits=[], historique={}, historique_js={}, active="product_history")
    finally:
        cursor.close()
        db.close()

@app.route('/users')
@login_required
@admin_required
def users():
    """Liste tous les utilisateurs (admin uniquement)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT Id_User, UserName, email, role FROM User")
        users_list = cursor.fetchall()
        return render_template('users.html', users=users_list, active="users")
    except Exception as e:
        flash(f"Erreur: {str(e)}", "danger")
        return render_template('users.html', users=[], active="users")
    finally:
        cursor.close()
        conn.close()

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """Ajoute un nouvel utilisateur"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        hashed_password = generate_password_hash('MotDePasseTemporaire123')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO User (UserName, email, role, password) VALUES (%s, %s, %s, %s)",
                (username, email, role, hashed_password)
            )
            conn.commit()
            
            token = serializer.dumps(email, salt='reset-password')
            reset_link = url_for('reset_password', token=token, _external=True)
            flash(f"Utilisateur ajouté avec succès! Lien de création de mot de passe: {reset_link}", "success")
            return redirect(url_for('users'))
        except mysql.connector.IntegrityError:
            conn.rollback()
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for('add_user'))
        except Exception as e:
            flash(f"Erreur: {str(e)}", "danger")
            return redirect(url_for('add_user'))
        finally:
            cursor.close()
            conn.close()
    
    return render_template('add_user.html')

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Modifie un utilisateur"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        
        try:
            cursor.execute(
                "UPDATE User SET UserName = %s, email = %s, role = %s WHERE Id_User = %s",
                (username, email, role, user_id)
            )
            conn.commit()
            flash("Utilisateur mis à jour avec succès!", "success")
            return redirect(url_for('users'))
        except Exception as e:
            flash(f"Erreur: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()
    else:
        try:
            cursor.execute("SELECT * FROM User WHERE Id_User = %s", (user_id,))
            user = cursor.fetchone()
            return render_template('edit_user.html', user=user)
        except Exception as e:
            flash(f"Erreur: {str(e)}", "danger")
            return redirect(url_for('users'))
        finally:
            cursor.close()
            conn.close()

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Supprime un utilisateur"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM User WHERE Id_User = %s", (user_id,))
        conn.commit()
        flash("Utilisateur supprimé avec succès!", "success")
    except Exception as e:
        flash(f"Erreur: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('users'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Page des paramètres"""
    if request.method == 'POST':
        flash("Paramètres mis à jour avec succès!", "success")
        return redirect(url_for('settings'))
    return render_template('settings.html', active="settings")


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)