import subprocess
from waitress import serve
from flask import Flask, jsonify, send_from_directory, request
import os
app = Flask(__name__)

#Recuperation du SSID
def get_ssid():
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'interfaces'],
        capture_output=True,
        text=True,
        encoding="cp850"
,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    #Boucle pour recuper la ligne contenant le SSID
    for line in result.stdout.splitlines():
        if "SSID" in line and "BSSID" not in line:
            ssid = line.split(":")[1].strip()
            return ssid
    
#Recuperation du mot de passe
def get_password(ssid):
    #Affichage de la commande pour recuperer le mot de passe
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'profile', f'name={ssid}' ,'key=clear'],
        capture_output=True,
        text=True,
        encoding="cp850"
,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    #Recuperation de la ligne contenant le mot de passe
    for line in result.stdout.splitlines():
        if "Key Content" in line or "Contenu de la clé" in line:
            password = line.split(":",1 )[1].strip()
            return password

#Recuperation de la securite du reseau
def get_security():
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'interfaces'],
        capture_output=True,
        text=True,
        encoding="cp850"
,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    for line in result.stdout.splitlines():
        if "Authentification" in line:
            security = line.split(":",1)[1].strip()
            return security
# Creation de la route pour la page d'accueil
@app.route('/')
def index():
    return send_from_directory('.', 'index.html') 

# Creation de la route pour la page de scan
@app.route('/scan')
def scanner():
    #instructions
    ssid = get_ssid()
    password = get_password(ssid)
    security = get_security()
    return jsonify({
        "ssid": ssid,
        "password": password,
        "security": security
    })
    
     
@app.route('/change_password', methods=['POST'])
def recup_values():
    #Get username
    username = os.getenv('USERNAME')
    print(username)
    
    #Recuperation des données
    data = request.get_json()
    old_Password = data['old_password']
    new_Password = data['new_password']
    confirm_Password = data['confirm_password']
    
    if new_Password != confirm_Password:
        return jsonify({"error": "Les nouveaux mots de passe ne correspondent pas"})  # quel message ?

    # Tentative de changement direct
    result = subprocess.run(
        f'net user "{username}" "{new_Password}"',
        capture_output=True,
        text=True,
        shell=True
    )

    if result.returncode != 0:
        # Compte Microsoft ou erreur → redirection
        subprocess.run('start ms-settings:signinoptions-passwordchange', shell=True)
        return jsonify({"error": "Compte Microsoft détecté. Redirection vers la page de changement..."})
    
    return jsonify({"success": True})
    
if __name__ == '__main__':
    # waitress = serveur WSGI Windows, un seul processus, pas de reloader
    serve(app, host='127.0.0.1', port=5000)