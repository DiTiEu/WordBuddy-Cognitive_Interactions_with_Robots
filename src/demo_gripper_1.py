import socket
import time
from utils import load_config
from robot_control import Robot
import os

HOST = "10.10.73.237"    # <-- metti l'IP GIUSTO del robot
PORT = 30002

# nomi file script gripper (gli stessi che hai sul PC)
SCRIPT_APRI  = "pinza40UR3.py"
SCRIPT_CHIUDI = "pinza10UR3.py"

def send_script_file(sock, path):
    """Invia il contenuto di un file .py/.script al robot tramite socket."""
    with open(path, "rb") as f:
        data = f.read()
    sock.sendall(data)

def main():
    # 1) Connessione socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"Connessione a {HOST}:{PORT} ...")
    sock.connect((HOST, PORT))
    print("✅ Connesso.")

    # 2) Popup di test sul pendant (per verificare connessione/stato robot)
    popup_cmd = 'popup("Test connessione grip", title="PC → UR3", warning=False)\n'
    sock.sendall(popup_cmd.encode("utf-8"))
    input("Se vedi il popup sul pendant, premi INVIO per continuare...")

    # 3) APRI pinza
    input("Premi INVIO per APRIRE la pinza...")
    send_script_file(sock, SCRIPT_APRI)
    time.sleep(1.0)


    # 4) CHIUDI pinza
    input("Premi INVIO per CHIUDERE la pinza...")
    send_script_file(sock, SCRIPT_CHIUDI)
    time.sleep(1.0)

    print("Test grip completato.")
    sock.close()

if __name__ == "__main__":
    main()
