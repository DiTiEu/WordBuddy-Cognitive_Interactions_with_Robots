import time
from utils import load_config
from robot_control import Robot

# Configurazione manuale per il test (o usa load_config se preferisci)
ROBOT_IP = "10.10.73.237" # <--- INSERISCI IL TUO IP
PORT = 30002

# Finti dati di config per inizializzare la classe
mock_poses = {}
mock_safety = {"max_speed": 0.1, "max_acc": 0.2} # Velocità basse per sicurezza

def main():
    print("--- TEST MOVEL CARTESIANO ---")
    
    # 1. Inizializza il robot
    robot = Robot(ROBOT_IP, mock_poses, mock_safety, port=PORT)
    
    if robot._simulated:
        print("⚠️ Sei in modalità simulata (nessuna connessione). Controlla l'IP.")
    else:
        print("✅ Connesso al robot.")

    # ---------------------------------------------------------
    # 2. DEFINISCI LA POSIZIONE TARGET (COPIA DAL PENDANT!)
    # ---------------------------------------------------------
    # Esempio: X=0.3m, Y=-0.2m, Z=0.2m
    # Rotazione (rx, ry, rz): Esempio pinza che guarda in basso.
    # ATTENZIONE: Sostituisci questi valori con una posa raggiungibile dal tuo robot!
    
    target_x = 0.360
    target_y = -0.148
    target_z = 0.207
    
    target_rx = 2.22  # Valori tipici UR3 verticale, MA VERIFICA I TUOI
    target_ry = -2.32
    target_rz = 0.114
    
    # Lista completa [x, y, z, rx, ry, rz]
    target_pose = [target_x, target_y, target_z, target_rx, target_ry, target_rz]

    input(f"Premi INVIO per muovere il robot linearmente a: {target_pose}")

    # 3. Esegui il movimento
    robot.move_linear(target_pose)

    print("Movimento inviato.")
    
    # Chiusura
    robot.close()

if __name__ == "__main__":
    main()