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

@app.route('/analytics')
def analytics():
    return render_template('product_history.html')

@app.route('/users')
def users():
    return render_template('users.html')
@app.route('/settings')
def settings():
    return render_template('settings.html')


if __name__ == "__main__":
    app.run(debug=True)
