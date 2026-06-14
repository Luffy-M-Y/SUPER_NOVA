import subprocess
from waitress import serve
from flask import Flask, jsonify, send_from_directory, request
import os
import win32security
import win32con
import ctypes
from flask import send_file
app = Flask(__name__)
 
# ════════════════════════════════════════
# SECTION 1 : RÉCUPÉRATION DONNÉES WIFI
# ════════════════════════════════════════

@app.route('/download')
def download():
    print("=== DOWNLOAD ROUTE APPELÉE ===", flush=True)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(base_dir, 'SUPER_NOVA_SETUP.exe')
    
    print(f"exe_path: {exe_path}", flush=True)
    print(f"exists: {os.path.exists(exe_path)}", flush=True)
    
    if os.path.exists(exe_path):
        try:
            print(f"Taille: {os.path.getsize(exe_path)}", flush=True)
            return send_file(exe_path, as_attachment=True, download_name='SUPER_NOVA_SETUP.exe')
        except Exception as e:
            print(f"✗ Erreur: {e}", flush=True)
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "fichier manquant"}), 404

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

print(f"Flask admin: {is_admin()}")

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
        encoding="cp65001",
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
        encoding="cp65001",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print("=== SORTIE NETSH ===")
    print(result.stdout)
    print("=== FIN ===")
    
    #Recuperation de la ligne contenant le mot de passe
    for line in result.stdout.splitlines():
        if ("Key Content" in line or           # Anglais
            "Contenu de la cl" in line or      # Français
            "Contenido de la clave" in line or # Espagnol
            "Schlüsselinhalt" in line or       # Allemand
            "Contenuto chiave" in line or      # Italien
            "Conteúdo da chave" in line or     # Portugais
            "Содержимое ключа" in line or      # Russe
            "Ključni sadržaj" in line or       # Croate
            "Inhoud van sleutel" in line or    # Néerlandais
            "Nyckel innehåll" in line or       # Suédois
            "Treści klucza" in line or         # Polonais
            "Obsah klíče" in line or           # Tchèque
            "キーコンテンツ" in line or         # Japonais
            "密钥内容" in line or               # Chinois simplifié
            "金鑰內容" in line):                # Chinois traditionnel:
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
        encoding="cp65001",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    for line in result.stdout.splitlines():
        if ("Authentification" in line or           # Français
            "Authentication" in line or             # Anglais
            "Autenticación" in line or              # Espagnol
            "Authentifizierung" in line or          # Allemand
            "Autenticazione" in line or             # Italien
            "Autenticação" in line or               # Portugais
            "Аутентификация" in line or             # Russe
            "Autentifikacija" in line or            # Croate
            "Authenticatie" in line or              # Néerlandais
            "Autentisering" in line or              # Suédois
            "Uwierzytelnianie" in line or           # Polonais
            "Ověření" in line or                    # Tchèque
            "認証" in line or                        # Japonais
            "身份验证" in line or                    # Chinois simplifié
            "驗證" in line):                         # Chinois traditionnel
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
    return send_from_directory('.', 'app.html') 
 
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
        ['powershell', '-Command', f'Get-LocalUser -Name "{username}" | Select-Object PasswordRequired'],
        capture_output=True,
        text=True,
        encoding="cp850",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print("=== SORTIE CHECK PASSWORD REQUIRED ===")
    print(password_exig.stdout)
    if password_exig.returncode == 0:
        if "False" in password_exig.stdout:
            print("Mot de passe non exigé")
            return False
        else:
            print("Mot de passe exigé")
            return True
 
    
 
# ════════════════════════════════════════
# SECTION 4 : VÉRIFICATION MOT DE PASSE
# ════════════════════════════════════════
@app.route('/has_password')
def has_password_route():
    try:
        with open(os.path.join(os.getenv('APPDATA'), 'user.txt'), 'r') as f:
            username = f.read().strip()
    except:
        username = os.getenv('USERNAME')
    
    print(f"has_password result = {has_password(username)}")
    
    return jsonify({"has_password": has_password(username)})

def has_password(username):
    # Vérifie PasswordLastSet
    result = subprocess.run(
        ['powershell', '-Command', f'Get-LocalUser -Name "{username}" | Select-Object PasswordLastSet'],
        capture_output=True, text=True, encoding="cp850",
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    if "/" not in result.stdout and ":" not in result.stdout:
        return False  # jamais eu de mdp
    
    # A eu un mdp → vérifie avec LogonUser si toujours actif
    try:
        win32security.LogonUser(
            username, None, '',
            win32con.LOGON32_LOGON_NETWORK,
            win32con.LOGON32_PROVIDER_DEFAULT
        )
        return False  # mdp vide réussit = pas de mdp
    except:
        return True
    
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

def check_account_password_status(username):
    try:
        ps_cmd = f'''Add-Type -AssemblyName System.DirectoryServices.AccountManagement
$context = New-Object System.DirectoryServices.AccountManagement.PrincipalContext('Machine')
$context.ValidateCredentials('{username}', '')'''
        result = subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True, text=True, encoding="cp850", creationflags=subprocess.CREATE_NO_WINDOW)
        
        print(f"PowerShell stdout: '{result.stdout}'")
        print(f"PowerShell stderr: '{result.stderr}'")
        print(f"PowerShell returncode: {result.returncode}")
        
        if "MethodInvocationException" in result.stderr or "PrincipalOperationException" in result.stderr:
            return False
        
        return 'True' in result.stdout
    except Exception as e:
        print(f"Exception: {e}")
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

@app.route('/confirmation.html')
def confirmation():
    return send_from_directory('.', 'confirmation.html')

@app.route('/change_password', methods=['POST'])         
def recup_values():
    if not is_admin():
        return jsonify({"error": "Admin requis. Relance l'app en admin."})
    print('recup value')
    # Étape 1 : Récupère username
    # Lit user.txt (créé par run.bat AVANT élévation admin)
    # Fallback : os.getenv('USERNAME') si fichier absent
    try:
        with open(os.path.join(os.getenv('APPDATA'), 'user.txt'), 'r') as f:
            username = f.read().strip()
    except:
        username = os.getenv('USERNAME')
 
    print(f"Username utilisé: {username}")
    print(f"USERNAME Admin: {os.getenv('USERNAME')}")
    
    # Étape 2 : Récupère données du formulaire
    data = request.get_json()
    print(f"data reçu = {data}")
    old_Password = old_Password = data.get('old_password', '')
    new_Password = data['new_password']
    confirm_Password = data['confirm_password']
    
    # Étape 3 : Valide que les deux nouveaux mdp correspondent
    if new_Password != confirm_Password:
        return jsonify({"error": "Les nouveaux mots de passe ne correspondent pas."})
     
    # Étape 4 : Vérifie type de compte (sécurité requise ou non)
    result_check = check_passord_required(username)
    print(f"check_passord_required = {result_check}")
    
    if result_check == False:
        print('Mot de passe non exigé')
    
        # Lance PowerShell pour test
        ps_cmd = f'''Add-Type -AssemblyName System.DirectoryServices.AccountManagement
        $context = New-Object System.DirectoryServices.AccountManagement.PrincipalContext('Machine')
        $context.ValidateCredentials('{username}', '')'''
        result = subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
        
        print(f"PowerShell returncode: {result.returncode}")
        
        # SI vide + exception (returncode=1) → accept
        if old_Password == '' and result.returncode == 1:
            print("mot de passe vide")
            proceed = True
        # SINON SI non-vide + mdp correct → accept
        elif old_Password != '' and verifier_ancien_mdp(username, old_Password):
            print("L'ancien mot de passe correspond")
            proceed = True
        else:
            print("aucun d'eux ne fonctonne")
            proceed = False

        if proceed:
            result = subprocess.run(
            ['net', 'user', username, new_Password],
            capture_output=True,
            encoding="cp850",
            text=True
        )
            print(f'returncode: {result.returncode}')
            print(f'stdout: {result.stdout}')
            print(f'stderr: {result.stderr}')
            
            if result.returncode == 0:
                return jsonify({"success": True})
            else:
                return jsonify({"error": f"net user échoué (code {result.returncode})"})
        else:
            return jsonify({"error": "Mot de passe actuel incorrect"})
    else:
        # CAS 2 : "Mot de passe exigé = Oui"
        # → Impossible via CLI, redirection Settings
        subprocess.run('start ms-settings:signinoptions', shell=True)
        return jsonify({"error": "Compte Microsoft détecté. Redirection vers les paramètres de connexion manuels..."})
 
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