"""SUPER NOVA Recovery - gestionnaire Windows local.

Version initiale non destructive : vérifie l'ISO et liste les lecteurs
amovibles, sans formater ni écrire sur aucun disque.
"""

import json
import os
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ISO_PATH = os.path.join(BASE_DIR, "output", "SUPER_NOVA_RECOVERY.iso")


def list_usb_drives():
    command = (
        "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=2\" | "
        "Select-Object DeviceID,VolumeName | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True, text=True, encoding="cp850",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    return [
        (item.get("DeviceID", ""), item.get("VolumeName") or "Disque amovible")
        for item in data if item.get("DeviceID")
    ]


def refresh_drives():
    drive_list.delete(0, tk.END)
    drives = list_usb_drives()
    if not drives:
        drive_list.insert(tk.END, "Aucune clé USB détectée")
        return
    for letter, label in drives:
        drive_list.insert(tk.END, f"{letter} - {label}")


def show_iso_status():
    if os.path.isfile(ISO_PATH):
        size_mb = os.path.getsize(ISO_PATH) / (1024 * 1024)
        iso_status.config(text=f"ISO prête ({size_mb:.0f} Mo)", foreground="#39e681")
    else:
        iso_status.config(text="ISO introuvable", foreground="#ff5555")


def not_implemented_yet():
    messagebox.showinfo(
        "Étape suivante",
        "L’écriture de l’ISO sera ajoutée après validation de la détection USB.\n"
        "Aucune donnée ne sera supprimée pendant cette étape.",
    )


root = tk.Tk()
root.title("SUPER NOVA RECOVERY")
root.geometry("560x380")
root.configure(bg="#0a0e1a")
style = ttk.Style(root)
style.theme_use("clam")
style.configure("TLabel", background="#0a0e1a", foreground="#e0e0e0", font=("Segoe UI", 11))
style.configure("TButton", font=("Segoe UI", 10))

ttk.Label(root, text="SUPER NOVA RECOVERY", font=("Segoe UI", 20, "bold")).pack(pady=(24, 8))
iso_status = ttk.Label(root, text="Vérification de l'ISO...")
iso_status.pack(pady=4)
ttk.Label(root, text="Clés USB amovibles détectées :").pack(pady=(20, 6))
drive_list = tk.Listbox(root, height=6, width=52, bg="#111827", fg="#e0e0e0", selectbackground="#245ca8")
drive_list.pack()
button_frame = tk.Frame(root, bg="#0a0e1a")
button_frame.pack(pady=18)
ttk.Button(button_frame, text="Actualiser", command=refresh_drives).pack(side=tk.LEFT, padx=6)
ttk.Button(button_frame, text="Créer la clé (bientôt)", command=not_implemented_yet).pack(side=tk.LEFT, padx=6)
show_iso_status()
refresh_drives()
root.mainloop()
