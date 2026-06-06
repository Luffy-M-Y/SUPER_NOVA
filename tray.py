import subprocess # lance app.py
import pystray       # gère l'icône système
from PIL import Image, ImageDraw # crée l'icône (image)
import webbrowser     # ouvre le navigateur
import threading      # lance Flask sans bloquer pystray

flask_process = None  # variable globale

def lancer_flask():
    global flask_process
    flask_process = subprocess.Popen(
        ['pythonw', 'app.py'],
        creationflags=subprocess.CREATE_NO_WINDOW
    )

def quitter_icone(icon, item):
    if flask_process:
        flask_process.terminate()  # ← tue Flask
    icon.stop()  # arrête l'icône et le programme
    
def creer_icone():
    image = Image.new('RGB', (64, 64), color='#0a0e1a')
    draw = ImageDraw.Draw(image)
    draw.ellipse([8, 8, 56, 56], fill='#3a7bd5')
    return image

def ouvrir_navigateur():
    webbrowser.open('http://127.0.0.1:5000/')   # ouvre le navigateur sur l'adresse localhost

def quitter_icone(icon, item):
    icon.stop()  # arrête l'icône et le programme   
    
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
        name='Wi-Fi Scanner',
        icon=creer_icone(),
        title='Wi-Fi Scanner',
        menu=menu
    )

    icone.run()