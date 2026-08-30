import ctypes
import sys
import os
import time
import socket
import subprocess # lance app.py
import pystray       # gère l'icône système
from PIL import Image, ImageDraw # crée l'icône (image)
import webbrowser     # ouvre le navigateur
import threading      # lance Flask sans bloquer pystray
import app as flask_app
import webview

def is_admin():
    return ctypes.windll.shell32.IsUserAnAdmin()

if not is_admin():
    # Sauvegarde username avant élévation
    with open(os.path.join(os.getenv('APPDATA'), 'user.txt'), 'w') as f:
        f.write(os.getenv('USERNAME'))
    
    # Relance en admin
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    with open(os.path.join(os.getenv('APPDATA'), 'debug_log.txt'), 'w') as f:
        f.write("Avant relance admin\n")
    sys.exit()
    
flask_process = None  # variable globale

def lancer_flask():
    flask_app.app.run(debug=False, use_reloader=False)


def attendre_flask(timeout=5.0):
    """Wait until Flask listens instead of sleeping for a fixed duration."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", 5000), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.05)
    return False

def quitter_icone(icon, item):
    icon.stop()
    os._exit(0)
    
def creer_icone():
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return Image.open(os.path.join(base, "SUPER_NOVA.ico"))

def ouvrir_fenetre():
    webview.create_window('SUPER NOVA', 'http://127.0.0.1:5000/')
    webview.start(icon='SUPER_NOVA.ico')
 
def ouvrir_navigateur_web():
    subprocess.run(
        ['explorer.exe', 'http://127.0.0.1:5000/'],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
       
if __name__ == '__main__':
    with open(os.path.join(os.getenv('APPDATA'), 'debug_log.txt'), 'a') as f:
        f.write(f"Démarrage - is_admin={is_admin()}\n")
    # Lance Flask dans un thread séparé
    thread = threading.Thread(target=lancer_flask)
    thread.start()

    # Crée le menu clic droit
    menu = pystray.Menu(
        pystray.MenuItem('Ouvrir', lambda icon, item: ouvrir_navigateur_web(), default=True),
        pystray.MenuItem('Quitter', quitter_icone)
    )

    # Crée et lance l'icône système
    icone = pystray.Icon(
        name='SUPER NOVA',
        icon=creer_icone(),
        title='SUPER NOVA',
        menu=menu
    )
    
    if not attendre_flask():
        print("Flask n'a pas démarré dans le délai prévu.", flush=True)
    thread_tray = threading.Thread(target=icone.run)
    thread_tray.start()
    ouvrir_fenetre()
