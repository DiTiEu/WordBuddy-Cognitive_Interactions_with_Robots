import socket
import time

# --- CONFIGURAZIONE ---
ROBOT_IP = "10.10.73.237"  # Metti il tuo IP
PORT = 30002               # Porta standard per i comandi

def invia_comando(script_command):
    """Funzione base per inviare testo al robot via socket"""
    try:
        # Crea il socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((ROBOT_IP, PORT))
        
        # Aggiungi il newline necessario alla fine
        if not script_command.endswith('\n'):
            script_command += '\n'
            
        # Invia codificato in utf-8
        s.sendall(script_command.encode('utf-8'))
        s.close()
        print("-> Comando inviato.")
    except Exception as e:
        print(f"ERRORE DI CONNESSIONE: {e}")

def muovi_relativo_cartesiano(dx_m, dy_m, dz_m, acc=0.5, vel=0.25):
    """
    Sposta il robot rispetto alla BASE (X, Y, Z del mondo), 
    mantenendo l'orientamento attuale della pinza.
    dx_m, dy_m, dz_m sono in METRI.
    """
    print(f"Sposto di X={dx_m}, Y={dy_m}, Z={dz_m}...")

    # Qui costruiamo lo script UR dinamicamente usando le f-strings di Python.
    # get_actual_tcp_pose() restituisce p[x,y,z,rx,ry,rz] rispetto alla BASE.
    ur_script = f"""
    def move_rel_python():
        # 1. Leggi dove sono ora
        p_now = get_actual_tcp_pose()
        
        # 2. Modifico solo le coordinate cartesiane (Indici 0, 1, 2)
        # Lascio invariati rx, ry, rz (Indici 3, 4, 5) per non far ruotare la pinza
        p_target = p_now
        p_target[0] = p_now[0] + {dx_m}
        p_target[1] = p_now[1] + {dy_m}
        p_target[2] = p_now[2] + {dz_m}

        # 3. Messaggio di debug sul Log del robot
        textmsg("Python Target Z:", p_target[2])

        # 4. Eseguo il movimento lineare
        movel(p_target, a={acc}, v={vel})
    end
    move_rel_python()
    """
    
    invia_comando(ur_script)

# --- ESECUZIONE DEL TEST ---
if __name__ == "__main__":
    print("--- TEST MOVEL SENZA LIBRERIE ---")
    print("Assicurati che il robot sia in REMOTE e non in Stop.")
    
    # 1. Test movimento verso l'ALTO (Z positivo)
    input("Premi INVIO per salire di 5 cm (Z+0.05)...")
    muovi_relativo_cartesiano(0.0, 0.0, 0.05) 

    # Attesa per far finire il movimento (poiché la socket non aspetta da sola)
    time.sleep(3.0)

    # 2. Test movimento verso il BASSO (Z negativo)
    input("Premi INVIO per scendere di 5 cm (Z-0.05)...")
    muovi_relativo_cartesiano(0.0, 0.0, -0.05)
    
    print("Test finito.")