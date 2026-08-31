import subprocess
import json
from flask import Flask, jsonify, send_from_directory, request
import os
import win32security
import win32con
import win32net
import win32netcon
import ctypes
from flask import send_file

ERROR_ACCOUNT_RESTRICTION = 1327

app = Flask(__name__)
_location_required_at_startup = None
 
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

def run_netsh(*args):
    """Run netsh using the Windows console encoding."""
    result = subprocess.run(
        ["netsh", *args],
        capture_output=True,
        text=True,
        encoding="cp850",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=15,
    )
    return result.stdout


def netsh_location_required():
    """Detect the Windows location permission error returned by netsh."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    # Normaliser les espaces (Windows peut renvoyer des espaces insécables
    # dans la sortie française).
    output = " ".join(
        f"{result.stdout}\n{result.stderr}".casefold().replace("\xa0", " ").split()
    )
    markers = (
        "autorisation de localisation",
        "services de localisation",
        "privacy-location",
        "location permission",
        "localisation",
        "location",
        "wlanqueryinterface",
    )
    return any(marker in output for marker in markers)


def cache_location_status():
    """Pre-check location access without opening any Windows settings."""
    global _location_required_at_startup
    _location_required_at_startup = netsh_location_required()
    return _location_required_at_startup


def location_required_for_scan():
    """Refresh location access immediately before a Wi-Fi scan."""
    global _location_required_at_startup
    _location_required_at_startup = netsh_location_required()
    return _location_required_at_startup


def run_powershell(command, timeout=15):
    """Run PowerShell consistently and prevent a hung command from blocking Flask."""
    args = ['powershell', '-NoProfile', '-NonInteractive', '-Command', command]
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args, 124, stdout='', stderr='PowerShell command timed out'
        )


def get_target_username():
    """Return the user account selected before administrator elevation."""
    appdata = os.getenv('APPDATA')
    if appdata:
        try:
            with open(os.path.join(appdata, 'user.txt'), 'r', encoding='utf-8') as file:
                username = file.read().strip()
            if username:
                return username
        except OSError:
            pass
    return (os.getenv('USERNAME') or '').strip()


def value_after_colon(line):
    """Return a netsh field value, or None for a non-field line."""
    if ':' not in line:
        return None
    return line.split(':', 1)[1].strip()


def _password_state_path():
    base_dir = os.getenv('PROGRAMDATA') or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'SUPER_NOVA', 'password_state.json')


def _account_sid(username):
    try:
        sid, _, _ = win32security.LookupAccountName(None, username)
        return win32security.ConvertSidToStringSid(sid)
    except win32security.error:
        return None


def _load_saved_password_state(username):
    sid = _account_sid(username)
    if not sid:
        return None
    try:
        with open(_password_state_path(), 'r', encoding='utf-8') as state_file:
            states = json.load(state_file)
        state = states.get(sid)
        return state if isinstance(state, bool) else None
    except (OSError, json.JSONDecodeError):
        return None


def _save_password_state(username, has_password):
    sid = _account_sid(username)
    if not sid:
        return
    state_path = _password_state_path()
    try:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        try:
            with open(state_path, 'r', encoding='utf-8') as state_file:
                states = json.load(state_file)
            if not isinstance(states, dict):
                states = {}
        except (OSError, json.JSONDecodeError):
            states = {}
        states[sid] = bool(has_password)
        temporary_path = state_path + '.tmp'
        with open(temporary_path, 'w', encoding='utf-8') as state_file:
            json.dump(states, state_file)
        os.replace(temporary_path, state_path)
    except OSError:
        # L'état persistant est une aide de détection ; il ne doit jamais
        # empêcher une modification de mot de passe déjà réussie.
        pass

# Fonction 1.1 : Récupère SSID
# Exécute : netsh wlan show interfaces
# Parse : cherche ligne avec "SSID" (pas "BSSID")
# Retourne : nom du réseau WiFi
def get_ssid(output=None):
    if output is None:
        output = run_netsh('wlan', 'show', 'interfaces')
    
    #Boucle pour recuper la ligne contenant le SSID
    for line in output.splitlines():
        if "SSID" in line and "BSSID" not in line:
            ssid = value_after_colon(line)
            if ssid:
                return ssid
    
# Fonction 1.2 : Récupère mot de passe WiFi
# Exécute : netsh wlan show profile name=SSID key=clear
# Parse : cherche "Key Content" ou "Contenu de la cl"
# Retourne : mot de passe du réseau
def get_password(ssid):
    #Affichage de la commande pour recuperer le mot de passe
    output = run_netsh('wlan', 'show', 'profile', f'name={ssid}', 'key=clear')
    
    #Recuperation de la ligne contenant le mot de passe
    for line in output.splitlines():
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
            password = value_after_colon(line)
            if password is not None:
                return password
 
# Fonction 1.3 : Récupère type de sécurité WiFi
# Exécute : netsh wlan show interfaces
# Parse : cherche "Authentification"
# Retourne : type de sécurité (WPA2, WPA3, etc)
def get_security(output=None):
    if output is None:
        output = run_netsh('wlan', 'show', 'interfaces')
    
    for line in output.splitlines():
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
            security = value_after_colon(line)
            if security is None:
                continue
            security_lower = security.casefold()
            if "wpa3" in security_lower:
                return "WPA3-Enterprise" if (
                    "enterprise" in security_lower or "entreprise" in security_lower
                ) else "WPA3-Personal"
            if "wpa2" in security_lower:
                return "WPA2-Enterprise" if (
                    "enterprise" in security_lower or "entreprise" in security_lower
                ) else "WPA2-Personal"
            if "wpa" in security_lower:
                return "WPA-Personal"
            if "wep" in security_lower:
                return "WEP"
            if "open" in security_lower or "ouvert" in security_lower:
                return "Open"
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
    try:
        if location_required_for_scan():
            return jsonify({
                "error": "La localisation Windows est désactivée. Activez-la pour analyser le Wi-Fi.",
                "open_location_settings": True,
            }), 503
        interface_output = run_netsh('wlan', 'show', 'interfaces')
        ssid = get_ssid(interface_output)
        if not ssid:
            return jsonify({
                "error": "Aucun réseau Wi-Fi connecté ou interface introuvable."
            }), 503

        password = get_password(ssid)
        security = get_security(interface_output)
        return jsonify({
            "ssid": ssid,
            "password": password,
            "security": security
        })
    except (OSError, subprocess.SubprocessError, ValueError):
        return jsonify({
            "error": "Impossible de lire les informations Wi-Fi."
        }), 503
 
# ════════════════════════════════════════
# SECTION 3 : VÉRIFICATION SÉCURITÉ COMPTE POUR LE CHANGEMENT DU MOT DE PASSE 
# ════════════════════════════════════════
 
# Fonction 3.1 : détecte la source du compte Windows
# Un compte local peut exiger un mot de passe : PasswordRequired ne permet
# donc pas de distinguer correctement un compte local d'un compte Microsoft.
def is_microsoft_account(username):
    ps_cmd = (
        f'$user = Get-LocalUser -Name "{username}" -ErrorAction Stop; '
        'Write-Output ([int]$user.PrincipalSource)'
    )
    try:
        result = run_powershell(ps_cmd)
    except OSError:
        return False

    if result.returncode != 0:
        return False

    source = result.stdout.strip().lower()
    return source in {'4', 'microsoftaccount'}
 
    
 
# ════════════════════════════════════════
# SECTION 4 : VÉRIFICATION MOT DE PASSE
# ════════════════════════════════════════
@app.route('/has_password')
def has_password_route():
    username = get_target_username()
    password_exists = has_password(username)
    if password_exists is None:
        # Certaines stratégies Windows rendent l'état indétectable. Le client
        # affiche alors un choix explicite au lieu de deviner ou de bloquer.
        return jsonify({
            "has_password": None,
            "state_unknown": True,
        })
    return jsonify({"has_password": password_exists})

def has_password(username):
    if not username:
        return None

    # Vérifie que le compte cible existe sans dépendre de la langue de Windows.
    try:
        account_info = win32net.NetUserGetInfo(None, username, 1)
    except win32net.error:
        return None

    # UF_PASSWD_NOTREQD est le signal explicite de Windows pour un compte
    # dont le mot de passe n'est pas requis.
    flags = int(account_info.get('flags', 0) or 0)
    if flags & win32netcon.UF_PASSWD_NOTREQD:
        return False

    # Le marqueur est une mémoire de dernier recours, jamais une priorité
    # sur l'état actuel du compte Windows.
    saved_state = _load_saved_password_state(username)

    # Tester d'abord une connexion vide en mode interactif local. Les
    # connexions réseau peuvent être bloquées par la stratégie Windows même
    # quand le compte n'a réellement aucun mot de passe.
    account_restricted = False
    for logon_type in (
        win32con.LOGON32_LOGON_INTERACTIVE,
        win32con.LOGON32_LOGON_NETWORK,
    ):
        try:
            win32security.LogonUser(
                username, None, '',
                logon_type,
                win32con.LOGON32_PROVIDER_DEFAULT
            )
            return False
        except win32security.error as error:
            # ERROR_ACCOUNT_RESTRICTION (1327) est renvoyée par Windows
            # lorsqu'un compte sans mot de passe est bloqué par la stratégie
            # « mots de passe vides uniquement en ouverture locale ».
            error_code = getattr(error, 'winerror', None)
            if error_code is None and error.args:
                error_code = error.args[0]
            if error_code == 1327:
                account_restricted = True
            continue

    # PasswordLastSet complète le test lorsque la stratégie locale refuse
    # également LogonUser en mode interactif.
    safe_username = username.replace("'", "''")
    password_state = run_powershell(
        "$ErrorActionPreference = 'Stop'; "
        f"$account = Get-LocalUser -Name '{safe_username}'; "
        "if ($null -eq $account.PasswordLastSet) { 'EMPTY' } else { 'SET' }",
        timeout=5,
    )
    if password_state.returncode == 0:
        state = password_state.stdout.strip().upper()
        if state == 'EMPTY':
            return False
        if state == 'SET':
            # PasswordLastSet peut rester renseigné après une suppression.
            # Un état enregistré par l'application peut alors corriger cette
            # ambiguïté, tout en laissant Windows prioritaire quand il indique
            # explicitement un compte sans mot de passe.
            return True if saved_state is None else saved_state

    # Dernier secours pour les systèmes qui ne fournissent pas
    # PasswordLastSet.
    password_age = int(account_info.get('password_age', 0) or 0)
    if (account_restricted or flags & win32netcon.UF_PASSWD_NOTREQD) and password_age == 0:
        return False
    if password_age != 0:
        return True if saved_state is None else saved_state
    return saved_state
    
# Fonction 4.1 : Vérifie ancien mot de passe
# Utilise : win32security.LogonUser (API Windows)
# Logique :
#   - Tente une connexion test avec username + ancien mdp
#   - Si succès → retourne True
#   - Si erreur → retourne False
# Limitation : Ne marche que si "Mot de passe exigé = Non"
def verifier_ancien_mdp(username,old_Password):
    token = None
    try:
        token = win32security.LogonUser(
            username,
            None,
            old_Password,
            win32con.LOGON32_LOGON_INTERACTIVE,
            win32con.LOGON32_PROVIDER_DEFAULT
        )
        return True
    except win32security.error as error:
        error_code = getattr(error, 'winerror', None)
        if error_code is None and error.args:
            error_code = error.args[0]
        # Avec un mot de passe vide, Windows peut refuser la connexion à
        # cause de la stratégie locale, même si le compte est réellement vide.
        if old_Password == '' and error_code == ERROR_ACCOUNT_RESTRICTION:
            return None
        return False
    finally:
        if token is not None:
            token.Close()


def account_allows_blank_password(username):
    """Return whether Windows marks the local account as not requiring a password."""
    try:
        account_info = win32net.NetUserGetInfo(None, username, 1)
    except win32net.error:
        return False
    flags = int(account_info.get('flags', 0) or 0)
    return bool(flags & win32netcon.UF_PASSWD_NOTREQD)


def verifier_mdp_actuel(username, password):
    """Verify the current password, including a policy-restricted blank one."""
    login_result = verifier_ancien_mdp(username, password)
    if password:
        return login_result is True
    if login_result is True:
        return True
    if login_result is None and account_allows_blank_password(username):
        return True

    # Dernier secours pour les systèmes où LogonUser ne répond pas directement.
    safe_username = username.replace("'", "''")
    ps_cmd = f'''Add-Type -AssemblyName System.DirectoryServices.AccountManagement
    $context = New-Object System.DirectoryServices.AccountManagement.PrincipalContext('Machine')
    $context.ValidateCredentials('{safe_username}', '')'''
    result = run_powershell(ps_cmd)
    return (
        result.returncode == 0
        and result.stdout.strip().casefold() == 'true'
    )

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
    # Étape 1 : Récupère username
    # Lit user.txt (créé par run.bat AVANT élévation admin)
    # Fallback : os.getenv('USERNAME') si fichier absent
    username = get_target_username()
 
    # Étape 2 : Récupère données du formulaire
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Données de formulaire invalides."}), 400

    old_Password = data.get('old_password', '')
    new_Password = data.get('new_password', '')
    confirm_Password = data.get('confirm_password', '')
    password_mode = data.get('password_mode')
    if password_mode is None:
        # Compatibilité avec les anciennes interfaces : le formulaire à deux
        # champs n'envoyait pas old_password.
        password_mode = 'empty' if 'old_password' not in data else 'has'
    if not isinstance(password_mode, str) or password_mode not in {'has', 'empty'}:
        return jsonify({"error": "État du mot de passe invalide."}), 400
    if not all(isinstance(value, str) for value in (
        old_Password, new_Password, confirm_Password
    )):
        return jsonify({"error": "Les mots de passe doivent être du texte."}), 400

    if password_mode == 'has' and not old_Password:
        return jsonify({"error": "Saisissez le mot de passe actuel."})
    if password_mode == 'empty':
        old_Password = ''
    
    # Étape 3 : Valide que les deux nouveaux mdp correspondent
    if new_Password != confirm_Password:
        return jsonify({"error": "Les nouveaux mots de passe ne correspondent pas."})
     
    # Étape 4 : vérifie la source réelle du compte
    if not is_microsoft_account(username):
        proceed = verifier_mdp_actuel(username, old_Password)

        if proceed:
            try:
                result = subprocess.run(
                    ['net', 'user', username, new_Password],
                    capture_output=True,
                    encoding="cp850",
                    errors="replace",
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=15
                )
            except subprocess.TimeoutExpired:
                return jsonify({
                    "error": "Le changement de mot de passe a dépassé le délai prévu."
                }), 504
            if result.returncode == 0:
                # Windows peut conserver une ancienne date PasswordLastSet
                # après la suppression du mot de passe. Mémoriser uniquement
                # l'état choisi, lié au SID (jamais le mot de passe), permet
                # de conserver une détection fiable après redémarrage.
                _save_password_state(username, bool(new_Password))
                return jsonify({"success": True})
            else:
                return jsonify({"error": f"net user échoué (code {result.returncode})"})
        else:
            return jsonify({"error": "Mot de passe actuel incorrect"})
    else:
        # CAS 2 : "Mot de passe exigé = Oui"
        # → Impossible via CLI. L'interface affichera d'abord le message,
        # puis demandera l'ouverture des paramètres Windows.
        return jsonify({
            "error": "Compte Microsoft détecté. Les paramètres de connexion vont s'ouvrir.",
            "open_settings": True
        })


@app.route('/restart_windows', methods=['POST'])
def restart_windows():
    """Schedule a local Windows restart after a successful password change."""
    if not is_admin():
        return jsonify({"error": "Droits administrateur requis."}), 403
    try:
        subprocess.Popen(
            ['shutdown.exe', '/r', '/t', '5'],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return jsonify({"success": True})
    except OSError:
        return jsonify({"error": "Impossible de planifier le redémarrage de Windows."}), 500


@app.route('/open_signin_settings', methods=['POST'])
def open_signin_settings():
    """Open Windows sign-in settings after the UI has displayed its message."""
    try:
        subprocess.Popen(
            'start "" ms-settings:signinoptions',
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return jsonify({"success": True})
    except OSError as error:
        return jsonify({"error": f"Impossible d'ouvrir les paramètres Windows : {error}"}), 500


@app.route('/open_location_settings', methods=['POST'])
def open_location_settings():
    """Open the Windows location privacy settings after a netsh denial."""
    try:
        subprocess.Popen(
            'start "" ms-settings:privacy-location',
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return jsonify({"success": True})
    except OSError as error:
        return jsonify({"error": f"Impossible d'ouvrir les paramètres de localisation : {error}"}), 500

# ════════════════════════════════════════
# SECTION 6 : LANCEMENT APPLICATION
# ════════════════════════════════════════
 
# Lance Flask en mode debug
# debug=True : rechargement auto si code change
# use_reloader=False : un seul processus (compatible avec pystray)
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
