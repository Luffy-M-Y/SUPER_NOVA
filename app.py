import subprocess
from waitress import serve
from flask import Flask, jsonify, send_from_directory, request
import os
import win32security
import win32con
app = Flask(__name__)

#Recuperation du SSID
def get_ssid():
    print('Yoooo',flush=True)
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'interfaces'],
        capture_output=True,
        text=True,
        encoding="cp850",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    #Boucle pour recuper la ligne contenant le SSID
    for line in result.stdout.splitlines():
        if "SSID" in line and "BSSID" not in line:
            ssid = line.split(":")[1].strip()
            print(ssid, flush=True)
            return ssid
    
#Recuperation du mot de passe
def get_password(ssid):
    #Affichage de la commande pour recuperer le mot de passe
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'profile', f'name={ssid}' ,'key=clear'],
        capture_output=True,
        text=True,
        encoding="cp850",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print("=== SORTIE NETSH ===")
    print(result.stdout)
    print("=== FIN ===")
    
    #Recuperation de la ligne contenant le mot de passe
    for line in result.stdout.splitlines():
        if "Key Content" in line or "Contenu de la cl" in line:
            print("cle trouvée")
            password = line.split(":",1 )[1].strip()
            return password

#Recuperation de la securite du reseau
def get_security():
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'interfaces'],
        capture_output=True,
        text=True,
        encoding="cp850",
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
    
def check_passord_required(username):
    password_exig = subprocess.run(
        f'net user "{username}"',
        capture_output=True,
        text=True,
        encoding="cp850",
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    for ligne in password_exig.stdout.splitlines():
        if "exigé" in ligne or "Mot de passe exigé" in ligne:
            if "Non" in ligne or "non" in ligne:
                print("Sortie trouvé")
                print(ligne)
                return False
            else:
                return True
            
def verifier_ancien_mdp(username,old_Password):
    print(f"ancien mode de passe = {old_Password}")
    print("verification que l'ancien mot de passe correspond")
    try:
        win32security.LogonUser(
            username,      # nom du compte
            None,          # domaine (None = local)
            old_Password,      # mot de passe à vérifier
            win32con.LOGON32_LOGON_INTERACTIVE,
            win32con.LOGON32_PROVIDER_DEFAULT
        )
        return True
    except: 
        return False
    
@app.route('/change_password', methods=['POST'])         
def recup_values():
    #Get username
    try:
        with open('user.txt', 'r') as f:
            username = f.read().strip()
    except:
        username = os.getenv('USERNAME')

    print(f"Username utilisé: {username}")
    print(f"USERNAME Admin: {os.getenv('USERNAME')}")
    
    #Recuperation des données
    data = request.get_json()
    old_Password = data['old_password']
    new_Password = data['new_password']
    confirm_Password = data['confirm_password']
    
    if new_Password != confirm_Password:
        return jsonify({"error": "Les nouveaux mots de passe ne correspondent pas"})  # quel message ?

    if check_passord_required(username) == False:
        print('la sortie est trouvée mot de passe non exigé')

        if verifier_ancien_mdp(username, old_Password) == True:
            print("l'ancien mot de passe correspond")
            # Tentative de changement direct
            result = subprocess.run(
                f'net user "{username}" "{new_Password}"',
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0:
                return jsonify({"success": True})
            else:
                return jsonify({"error": "Changement échoué"})
        else:
            print("l'ancien mot de passe ne correspond pas")
            return jsonify({"error": "L'ancien mot de passe ne correspondent pas"})

    else:
        # Compte Microsoft ou erreur → redirection
        subprocess.run('start ms-settings:signinoptions', shell=True)
        return jsonify({"error": "Compte Microsoft détecté. Redirection vers la page de changement de mot de passe..."})
    
    return jsonify({"success": True})
    
if __name__ == '__main__':
    # waitress = serveur WSGI Windows, un seul processus, pas de reloader
    #serve(app, host='127.0.0.1', port=5000)
    app.run(debug=True, use_reloader=False)