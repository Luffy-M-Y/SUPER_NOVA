import ctypes
import sys
import os
import time
import subprocess # lance app.py
import pystray       # gère l'icône système
from PIL import Image, ImageDraw # crée l'icône (image)
import webbrowser     # ouvre le navigateur
import threading      # lance Flask sans bloquer pystray
import app as flask_app

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
    sys.exit()
    
flask_process = None  # variable globale

def lancer_flask():
    flask_app.app.run(debug=False, use_reloader=False)

def quitter_icone(icon, item):
    icon.stop()
    os._exit(0)
    
def creer_icone():
    base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return Image.open(os.path.join(base, "SUPER_NOVA.ico"))

def ouvrir_navigateur():
    subprocess.run(
        ['explorer.exe', 'http://127.0.0.1:5000/'],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
if __name__ == '__main__':
    # Lance Flask dans un thread séparé
    thread = threading.Thread(target=lancer_flask)
    thread.start()

    # Crée le menu clic droit
    menu = pystray.Menu(
        pystray.MenuItem('Ouvrir', lambda icon, item: ouvrir_navigateur(), default=True),
        pystray.MenuItem('Quitter', quitter_icone)
    )

    # Crée et lance l'icône système
    icone = pystray.Icon(
        name='SUPER NOVA',
        icon=creer_icone(),
        title='SUPER NOVA',
        menu=menu
    )
    
    time.sleep(2)
    icone.run()