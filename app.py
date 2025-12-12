from flask import Flask, render_template,request, redirect, url_for
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="Nassira Amhaoui",            
        password="Nassira2005",
        database="gestion_stock" 
    )
@app.route('/')
def dashboard():
    return render_template('dashboard.html')
@app.context_processor
def inject_notifications():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT Nom, Quantite FROM Produit WHERE Quantite < 2")
    produits_faible = cursor.fetchall()
    cursor.close()
    
    notif_count = len(produits_faible)  # nombre de notifications
    
    return dict(produits_faible=produits_faible, notif_count=notif_count)


@app.route('/produits')
def produits():
    print("Route /produits appelée")  # <--- TEST
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produit")
    produits = cursor.fetchall()
    print("Données récupérées :", produits)  # <--- TEST
    cursor.close()
    db.close()
    
    return render_template("produits.html", produits=produits)


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
    
    return redirect(url_for('produits'))  # retour à la page produits

from flask import request, redirect, url_for

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

from collections import defaultdict
from datetime import datetime

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

    zoom = "month"  # exemple : "day", "month" ou "hour"

    # organiser historique par produit
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

        # Ajouter la clé dans l’objet h pour le regroupement si nécessaire
        h["zoom_key"] = key
        pid = h["Id_Produit"]
        historique_par_produit[pid].append(h)

    # Préparer structure JS-safe avec deux lignes : "ajouter" et "acheter"
    historique_js = {}
    for pid, entries in historique_par_produit.items():
        # tri chronologique
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
        active="historique"
    )

@app.route('/users')
def users():
    return render_template('users.html')
@app.route('/settings')
def settings():
    return render_template('settings.html')


if __name__ == "__main__":
    app.run(debug=True)
