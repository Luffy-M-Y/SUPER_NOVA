import subprocess
import json
import sys
import time
from flask import Flask, jsonify, send_from_directory, request
import os
import win32security
import win32con
import win32gui
import win32process
import win32net
import win32netcon
import ctypes
from flask import send_file
app = Flask(__name__)
ERROR_ACCOUNT_RESTRICTION = 1327
 
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
    result = run_hidden_command(["netsh", *args])
    return result.stdout


def run_hidden_command(args, timeout=15):
    """Run a Windows command with consistent output and timeout handling."""
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args, 124, stdout='', stderr='Command timed out'
        )


def netsh_location_required():
    """Detect the Windows location permission error returned by netsh."""
    try:
        result = run_hidden_command(["netsh", "wlan", "show", "interfaces"])
    except (OSError, subprocess.SubprocessError):
        return False
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
    """Pre-check location access without opening Windows settings."""
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
    return run_hidden_command(args, timeout=timeout)


def _local_account_exists(username):
    """Return whether *username* still exists as a local Windows account."""
    if not username:
        return False
    try:
        win32net.NetUserGetInfo(None, username, 1)
    except (OSError, win32net.error):
        return False
    return True


def get_target_username():
    """Return the pre-elevation account only when it is still valid/current."""
    appdata = os.getenv('APPDATA')
    current_username = (os.getenv('USERNAME') or '').strip()
    if appdata:
        try:
            with open(os.path.join(appdata, 'user.txt'), 'r', encoding='utf-8') as file:
                username = file.read().strip()
            if (
                username
                and _local_account_exists(username)
                and (
                    not current_username
                    or username.casefold() == current_username.casefold()
                )
            ):
                return username
        except OSError:
            pass
    return current_username


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
            password = line.split(":",1 )[1].strip()
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
    safe_username = username.replace("'", "''")
    ps_cmd = (
        f"$user = Get-LocalUser -Name '{safe_username}' -ErrorAction Stop; "
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
    password_required = account_password_required(username)
    if password_exists is None:
        return jsonify({
            "has_password": None,
            "state_unknown": True,
            "password_required": password_required,
        })
    return jsonify({
        "has_password": password_exists,
        "password_required": password_required,
    })

def has_password(username):
    if not username:
        return None
    try:
        account_info = win32net.NetUserGetInfo(None, username, 1)
    except win32net.error:
        return None

    flags = int(account_info.get('flags', 0) or 0)
    if flags & win32netcon.UF_PASSWD_NOTREQD:
        return False

    saved_state = _load_saved_password_state(username)
    account_restricted = False
    for logon_type in (
        win32con.LOGON32_LOGON_INTERACTIVE,
        win32con.LOGON32_LOGON_NETWORK,
    ):
        try:
            token = win32security.LogonUser(
                username, None, '',
                logon_type,
                win32con.LOGON32_PROVIDER_DEFAULT
            )
            close_handle = getattr(token, 'Close', None)
            if close_handle:
                close_handle()
            return False
        except win32security.error as error:
            error_code = getattr(error, 'winerror', None)
            if error_code is None and error.args:
                error_code = error.args[0]
            if error_code == ERROR_ACCOUNT_RESTRICTION:
                account_restricted = True

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
            return True if saved_state is None else saved_state

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
def verifier_ancien_mdp(username, old_Password):
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
        if old_Password == '' and error_code == ERROR_ACCOUNT_RESTRICTION:
            return None
        return False
    finally:
        if token is not None:
            close_handle = getattr(token, 'Close', None)
            if close_handle:
                try:
                    close_handle()
                except (OSError, win32security.error):
                    pass


def account_allows_blank_password(username):
    """Return whether Windows marks the local account as not requiring a password."""
    try:
        account_info = win32net.NetUserGetInfo(None, username, 1)
    except win32net.error:
        return False
    flags = int(account_info.get('flags', 0) or 0)
    return bool(flags & win32netcon.UF_PASSWD_NOTREQD)


def account_password_required(username):
    """Return Windows' password-required flag, or None if unavailable."""
    if not username:
        return None
    try:
        account_info = win32net.NetUserGetInfo(None, username, 1)
    except win32net.error:
        return None
    flags = int(account_info.get('flags', 0) or 0)
    return not bool(flags & win32netcon.UF_PASSWD_NOTREQD)


def verifier_mdp_actuel(username, password):
    """Verify the current password, including a policy-restricted blank one."""
    login_result = verifier_ancien_mdp(username, password)
    if password:
        return login_result is True
    if login_result is True:
        return True
    if login_result is None and account_allows_blank_password(username):
        return True

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

    if new_Password != confirm_Password:
        return jsonify({"error": "Les nouveaux mots de passe ne correspondent pas."})

    if not is_microsoft_account(username):
        proceed = verifier_mdp_actuel(username, old_Password)
        if proceed:
            # Keep Windows' password-required flag synchronized with the
            # value being written.  ``net user <name> ""`` alone can leave
            # PasswordRequired=True, making a successfully blank password
            # look like a configured password after the next reboot.
            password_requirement = (
                '/passwordreq:no' if not new_Password else '/passwordreq:yes'
            )
            result = run_hidden_command(
                ['net', 'user', username, new_Password, password_requirement],
                timeout=15,
            )
            if result.returncode == 124 and result.stderr == 'Command timed out':
                return jsonify({
                    "error": "Le changement de mot de passe a dépassé le délai prévu."
                }), 504
            if result.returncode == 0:
                _save_password_state(username, bool(new_Password))
                return jsonify({"success": True})
            return jsonify({"error": f"net user échoué (code {result.returncode})"})
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
        os.startfile('ms-settings:signinoptions')
        return jsonify({"success": True})
    except OSError as error:
        return jsonify({"error": f"Impossible d'ouvrir les paramètres Windows : {error}"}), 500


@app.route('/allow_blank_password', methods=['POST'])
def allow_blank_password():
    """Synchronize the local account policy after explicit user confirmation."""
    if not is_admin():
        return jsonify({"error": "Droits administrateur requis."}), 403

    username = get_target_username()
    if not username or is_microsoft_account(username):
        return jsonify({
            "error": "Cette correction est disponible uniquement pour un compte local."
        }), 400

    result = run_hidden_command(
        ['net', 'user', username, '/passwordreq:no'],
        timeout=15,
    )
    if result.returncode == 124 and result.stderr == 'Command timed out':
        return jsonify({"error": "La correction a dépassé le délai prévu."}), 504
    if result.returncode != 0:
        return jsonify({
            "error": f"Impossible de modifier la stratégie du compte (code {result.returncode})."
        }), 500
    return jsonify({"success": True, "password_required": False})


@app.route('/open_location_settings', methods=['POST'])
def open_location_settings():
    """Open Windows location privacy settings after a netsh denial."""
    try:
        os.startfile('ms-settings:privacy-location')
        return jsonify({"success": True})
    except OSError as error:
        return jsonify({"error": f"Impossible d'ouvrir les paramètres de localisation : {error}"}), 500

# ════════════════════════════════════════
# SECTION 5.5 : RÉCUPÉRATION MOT DE PASSE (WINPE)
# ════════════════════════════════════════

@app.route('/list_usb_drives', methods=['GET'])
def list_usb_drives():
    try:
        # DriveType=2 signifie "Disque amovible" (Clé USB)
        ps_cmd = 'Get-WmiObject Win32_LogicalDisk -Filter "DriveType=2" | Select-Object DeviceID, VolumeName | ConvertTo-Json'
        result = run_powershell(ps_cmd)
        
        if not result.stdout.strip():
            return jsonify({"drives": []})
            
        import json
        data = json.loads(result.stdout)
        
        # PowerShell renvoie un dictionnaire si 1 clé, une liste si plusieurs
        if isinstance(data, dict):
            data = [data]
            
        drives = []
        for d in data:
            drives.append({
                "letter": d.get("DeviceID", ""),
                "label": d.get("VolumeName", "") or "Disque Amovible"
            })
            
        return jsonify({"drives": drives})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/create_recovery_usb', methods=['POST'])
def create_recovery_usb():
    if not is_admin():
        return jsonify({"error": "Droits administrateur requis."})
        
    data = request.get_json()
    target_drive = data.get('target_drive')
    
    if not target_drive:
        return jsonify({"error": "Aucune clé USB sélectionnée."})
        
    # Chemin vers le fichier ZIP créé par Amazon Q
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SUPER_NOVA_RECOVERY.zip')
    
    if not os.path.exists(zip_path):
        return jsonify({"error": "L'image SUPER_NOVA_RECOVERY.zip est introuvable. Elle doit être générée par Amazon Q au préalable."})
        
    try:
        import zipfile
        target_path = target_drive + "\\"
        
        # Extraction du ZIP directement à la racine de la clé USB
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_path)
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": f"Erreur d'extraction : {str(e)}"})


def find_recovery_window():
    """Return the existing Recovery window handle, if one is open."""
    window_handle = None

    def check_window(hwnd, _):
        nonlocal window_handle
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip().lower()
        if "super nova recovery" in title:
            window_handle = hwnd

    try:
        win32gui.EnumWindows(check_window, None)
    except Exception:
        return None
    return window_handle


def focus_recovery_window(window_handle):
    """Restore and bring the existing Recovery window to the foreground."""
    try:
        win32gui.ShowWindow(window_handle, win32con.SW_RESTORE)
        win32gui.SetWindowPos(
            window_handle,
            win32con.HWND_TOP,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
        )
        win32gui.BringWindowToTop(window_handle)
        win32gui.SetForegroundWindow(window_handle)
    except Exception:
        pass


@app.route('/open_recovery_manager', methods=['POST'])
def open_recovery_manager():
    """Launch the bundled local recovery manager; never use the browser or network."""
    existing_window = find_recovery_window()
    if existing_window:
        focus_recovery_window(existing_window)
        return jsonify({"success": True, "already_open": True})

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    candidates = [
        (
            os.path.join(base_dir, 'recovery', 'recovery_manager.exe'),
            os.path.join(base_dir, 'recovery'),
        ),
        (
            os.path.join(os.path.dirname(base_dir), 'SUPER_NOVA_RECOVERY', 'dist', 'recovery_manager.exe'),
            os.path.join(os.path.dirname(base_dir), 'SUPER_NOVA_RECOVERY'),
        ),
        (
            os.path.join(os.path.dirname(base_dir), 'SUPER_NOVA_RECOVERY', 'recovery_manager.py'),
            os.path.join(os.path.dirname(base_dir), 'SUPER_NOVA_RECOVERY'),
        ),
    ]

    for manager_path, working_dir in candidates:
        if not os.path.isfile(manager_path):
            continue
        try:
            if manager_path.lower().endswith('.py'):
                process = subprocess.Popen([sys.executable, manager_path], cwd=working_dir)
            else:
                process = subprocess.Popen([manager_path], cwd=working_dir)

            # Popen confirme seulement le démarrage du processus. Attendre une
            # fenêtre visible évite d'arrêter l'animation du bouton trop tôt.
            # Le gestionnaire compilé peut prendre plusieurs secondes à charger
            # Tkinter et l'ISO depuis un dossier partagé.
            deadline = time.monotonic() + 30.0
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    return jsonify({
                        "error": "SUPER NOVA RECOVERY s'est fermé avant l'affichage de sa fenêtre."
                    }), 500

                existing_window = find_recovery_window()
                if existing_window:
                    focus_recovery_window(existing_window)
                    return jsonify({"success": True})

                window_handle = None

                def check_window(hwnd, _):
                    nonlocal window_handle
                    if not win32gui.IsWindowVisible(hwnd):
                        return
                    _, owner_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if owner_pid == process.pid:
                        window_handle = hwnd

                win32gui.EnumWindows(check_window, None)
                if window_handle:
                    focus_recovery_window(window_handle)
                    return jsonify({"success": True})
                time.sleep(0.1)

            return jsonify({"success": True})
        except OSError as error:
            return jsonify({"error": f"Impossible de lancer SUPER NOVA RECOVERY : {error}"}), 500

    return jsonify({
        "error": "Gestionnaire Recovery introuvable. Installez le dossier recovery avec recovery_manager.exe et son ISO."
    }), 404

 
# ════════════════════════════════════════
# SECTION 6 : LANCEMENT APPLICATION
# ════════════════════════════════════════
 
# Lance Flask en mode debug
# debug=True : rechargement auto si code change
# use_reloader=False : un seul processus (compatible avec pystray)
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
