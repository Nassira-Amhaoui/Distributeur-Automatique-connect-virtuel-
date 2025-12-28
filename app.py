from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import json
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
import os


app = Flask(__name__)
load_dotenv()  

app.secret_key = os.getenv('SECRET_KEY')


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
    return mysql.connector.connect(
        host="localhost",
        user="Nassira Amhaoui",
        password="Nassira2005",
        database="gestion_stock"
    )

def envoyer_email_admin(nom_produit, quantite):
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

@app.context_processor
def inject_notifications():
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
            envoyer_email_admin(p["Nom"], p["Quantite"])
            cursor.execute(
                "UPDATE Produit SET email_envoye = 1 WHERE Id_Produit = %s",
                (p["Id_Produit"],)
            )
            db.commit()

    cursor.close()
    db.close()

    return dict(
        produits_faible=produits_faible,
        notif_count=len(produits_faible)
    )

# ========== ROUTES ==========

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
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    
    if user and check_password_hash(user['password'], password):
        return redirect(url_for('dashboard'))
    else:
        flash("Email ou mot de passe incorrect!")
        return redirect(url_for('login_page'))

@app.route('/forget_password', methods=['GET', 'POST'])
def forget_password():
    reset_link = None
    if request.method == 'POST':
        email = request.form.get('email')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
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
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas")
            return redirect(url_for('reset_password', token=token))
        
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE User SET password = %s WHERE email = %s", 
                      (hashed_password, email))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("Mot de passe modifié avec succès!")
        return redirect(url_for('login_page'))
    
    return render_template('reset_password.html', email=email)

@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS total FROM Produit")
    total_produits = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) AS total FROM Produit")
    total_distributeurs = cursor.fetchone()['total']
    cursor.execute("SELECT * FROM Produit WHERE Quantite <= 5 ORDER BY Quantite ASC")
    produits_faible = cursor.fetchall()
    cursor.execute("""
        SELECT SUM(h.Quantite * p.Prix) AS total
        FROM Historique h
        JOIN Produit p ON h.Id_Produit = p.Id_Produit
        WHERE h.Action = 'acheter'
    """)
    total_revenus = cursor.fetchone()['total'] or 0
    cursor.execute("""
        SELECT SUM(h.Quantite * p.Prix) AS total
        FROM Historique h
        JOIN Produit p ON h.Id_Produit = p.Id_Produit
        WHERE h.Action = 'acheter' 
        AND MONTH(h.Date_Action) = MONTH(CURDATE())
        AND YEAR(h.Date_Action) = YEAR(CURDATE())
    """)
    revenus_mois = cursor.fetchone()['total'] or 0
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
    cursor.execute("SELECT Nom, Quantite FROM Produit ORDER BY Quantite DESC")
    stock_produits = cursor.fetchall()
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

    cursor.close()
    conn.close()

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

@app.route('/produits')
def produits():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produit")
    produits_list = cursor.fetchall()
    cursor.close()
    db.close()
    
    return render_template("produits.html", produits=produits_list, active="produits")

@app.route('/ajouter_produit', methods=['POST'])
def ajouter_produit():
    nom = request.form['nom']
    etage = request.form['etage']
    quantite = request.form['quantite']

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("INSERT INTO produit (Nom, N_Etage, Quantite) VALUES (%s, %s, %s)",
                   (nom, etage, quantite))
    db.commit()
    cursor.close()
    db.close()
    
    return redirect(url_for('produits'))

@app.route("/modifier_produit", methods=["POST"])
def modifier_produit():
    id_p = request.form["id"]
    nom = request.form["nom"]
    etage = request.form["etage"]
    quantite = request.form["quantite"]

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE produit SET Nom=%s, N_Etage=%s, Quantite=%s WHERE Id_Produit=%s",
        (nom, etage, quantite, id_p)
    )
    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for("produits"))

@app.route("/supprimer_produit", methods=["POST"])
def supprimer_produit():
    id_p = request.form["id"]

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM produit WHERE Id_Produit = %s", (id_p,))
    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for("produits"))

@app.route('/product_history')
def product_history():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

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

    cursor.close()
    db.close()

    return render_template(
        "product_history.html",
        produits=produits,
        historique=historique_par_produit,
        historique_js=historique_js,
        active="product_history"
    )

@app.route('/users')
def users():
    return render_template('users.html', active="users")

@app.route('/settings')
def settings():
    return render_template('settings.html', active="settings")


if __name__ == "__main__":
    app.run(debug=True)