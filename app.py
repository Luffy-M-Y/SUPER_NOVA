import subprocess
from waitress import serve
from flask import Flask, jsonify, send_from_directory, request
import os
import win32security
import win32con
app = Flask(__name__)
 
# ════════════════════════════════════════
# SECTION 1 : RÉCUPÉRATION DONNÉES WIFI
# ════════════════════════════════════════
 
# Fonction 1.1 : Récupère SSID
# Exécute : netsh wlan show interfaces
# Parse : cherche ligne avec "SSID" (pas "BSSID")
# Retourne : nom du réseau WiFi
def get_ssid():
    print('Yoooo',flush=True)
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'interfaces'],
        capture_output=True,
        text=True,
        encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    #Boucle pour recuper la ligne contenant le SSID
    for line in result.stdout.splitlines():
        if "SSID" in line and "BSSID" not in line:
            ssid = line.split(":")[1].strip()
            print(ssid, flush=True)
            return ssid
    
# Fonction 1.2 : Récupère mot de passe WiFi
# Exécute : netsh wlan show profile name=SSID key=clear
# Parse : cherche "Key Content" ou "Contenu de la cl"
# Retourne : mot de passe du réseau
def get_password(ssid):
    #Affichage de la commande pour recuperer le mot de passe
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'profile', f'name={ssid}' ,'key=clear'],
        capture_output=True,
        text=True,
        encoding="utf-8",
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
 
# Fonction 1.3 : Récupère type de sécurité WiFi
# Exécute : netsh wlan show interfaces
# Parse : cherche "Authentification"
# Retourne : type de sécurité (WPA2, WPA3, etc)
def get_security():
    result = subprocess.run(
        ['netsh', 'wlan', 'show', 'interfaces'],
        capture_output=True,
        text=True,
        encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    for line in result.stdout.splitlines():
        if "Authentification" in line:
            security = line.split(":",1)[1].strip()
            return security 
 
# ════════════════════════════════════════
# SECTION 2 : ROUTES FLASK
# ════════════════════════════════════════
 
# Route 2.1 : Page d'accueil
# URL : GET /
# Retourne : index.html
@app.route('/')
def index():
    return send_from_directory('.', 'index.html') 
 
# Route 2.2 : Scanner WiFi
# URL : GET /scan
# Exécute : appelle get_ssid() + get_password() + get_security()
# Retourne : JSON {ssid, password, security}
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
 
# ════════════════════════════════════════
# SECTION 3 : VÉRIFICATION SÉCURITÉ COMPTE POUR LE CHANGEMENT DU MOT DE PASSE 
# ════════════════════════════════════════
 
# Fonction 3.1 : Vérifie si mot de passe exigé
# Exécute : net user USERNAME
# Parse : cherche "Mot de passe exigé"
# Logique :
#   - Si "Non" → retourne False (pas exigé, peut changer avec net user directement)
#   - Si "Oui" → retourne True (exigé, besoin de redirection Settings)
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
 
# ════════════════════════════════════════
# SECTION 4 : VÉRIFICATION MOT DE PASSE
# ════════════════════════════════════════
 
# Fonction 4.1 : Vérifie ancien mot de passe
# Utilise : win32security.LogonUser (API Windows)
# Logique :
#   - Tente une connexion test avec username + ancien mdp
#   - Si succès → retourne True
#   - Si erreur → retourne False
# Limitation : Ne marche que si "Mot de passe exigé = Non"
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
 
# ════════════════════════════════════════
# SECTION 5 : CHANGEMENT MOT DE PASSE
# ════════════════════════════════════════
 
# Route 5.1 : Changer mot de passe Windows
# URL : POST /change_password
# Corps : {old_password, new_password, confirm_password}
# Logique :
#   1. Vérifie new_password == confirm_password
#   2. Vérifie si "Mot de passe exigé" sur le compte
#   3. Si Non → vérifie ancien mdp avec LogonUser, puis exécute net user
#   4. Si Oui → redirige vers MS Settings (pas de changement CLI possible)
@app.route('/change_password', methods=['POST'])         
def recup_values():
    # Étape 1 : Récupère username
    # Lit user.txt (créé par run.bat AVANT élévation admin)
    # Fallback : os.getenv('USERNAME') si fichier absent
    try:
        with open('user.txt', 'r') as f:
            username = f.read().strip()
    except:
        username = os.getenv('USERNAME')
 
    print(f"Username utilisé: {username}")
    print(f"USERNAME Admin: {os.getenv('USERNAME')}")
    
    # Étape 2 : Récupère données du formulaire
    data = request.get_json()
    old_Password = data['old_password']
    new_Password = data['new_password']
    confirm_Password = data['confirm_password']
    
    # Étape 3 : Valide que les deux nouveaux mdp correspondent
    if new_Password != confirm_Password:
        return jsonify({"error": "Les nouveaux mots de passe ne correspondent pas."})
 
    # Étape 4 : Vérifie type de compte (sécurité requise ou non)
    if check_passord_required(username) == False:
        # CAS 1 : "Mot de passe exigé = Non"
        # → Peut changer avec net user après vérification ancien mdp
        print('la sortie est trouvée mot de passe non exigé')
 
        if verifier_ancien_mdp(username, old_Password) == True:
            print("l'ancien mot de passe correspond")
            
            # Exécute : net user USERNAME NOUVEAUMDP
            result = subprocess.run(
                f'net user "{username}" "{new_Password}"',
                capture_output=True,
                encoding="utf-8",
                text=True,
                shell=True
            )
            
            # Vérifie si net user a réussi
            if result.returncode == 0:
                return jsonify({"success": True})
            else:
                return jsonify({"error": "Changement échoué"})
        else:
            # Ancien mdp incorrect
            print("l'ancien mot de passe ne correspond pas")
            return jsonify({"error": "Mot de passe actuel incorrect"})
 
    else:
        # CAS 2 : "Mot de passe exigé = Oui"
        # → Impossible via CLI, redirection Settings
        subprocess.run('start ms-settings:signinoptions', shell=True)
        return jsonify({"error": "Compte Microsoft détecté. Redirection vers les paramètres de connexion manuels..."})
    
    return jsonify({"success": True})
 
# ════════════════════════════════════════
# SECTION 6 : LANCEMENT APPLICATION
# ════════════════════════════════════════
 
# Lance Flask en mode debug
# debug=True : rechargement auto si code change
# use_reloader=False : un seul processus (compatible avec pystray)
if __name__ == '__main__':
    # waitress = serveur WSGI Windows, un seul processus, pas de reloader
    #serve(app, host='127.0.0.1', port=5000)
    app.run(debug=True, use_reloader=False)