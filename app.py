import subprocess
from flask import Flask, jsonify, send_from_directory
app = Flask(__name__)

#Recuperation du SSID
def get_ssid():
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'interfaces'],
        capture_output=True,
        text=True,
        encoding="utf-8"
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
        encoding="utf-8"
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
        encoding="utf-8"
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
    
if __name__ == '__main__':
    app.run(debug=True)