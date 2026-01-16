import time
import socket
from typing import List, Optional

class Robot:
    """
    Controllo UR tramite socket TCP.
    Versione aggiornata per gestire Config e Home sicura (MoveJ).
    """

    def __init__(self, robot_ip: str, config: dict):
        self.config = config or {}
        self.verbose = self.config.get("settings", {}).get("verbose", False)
        
        # --- RETE ---
        self.robot_ip = robot_ip
        self.port = self.config.get("robot", {}).get("port", 30002)
        self.sock: Optional[socket.socket] = None
        self._simulated = False

        # --- PARAMETRI ---
        safety = self.config.get("safety", {})
        self.max_speed = safety.get("speed", 0.1) 
        self.max_acc = safety.get("acc", 0.2)
        self.z_pick_offset = safety.get("z_pick_offset", -0.05)

        # Home Joints (Radianti)
        self.home_joints = self.config.get("robot", {}).get("home_joints")

        # Griglie e Slots
        self.grids_config = self.config.get("grids", [])
        self.cfg_slots = self.config.get("slots", {})

        self._connect()

    def _connect(self):
        if not self.robot_ip:
            print("⚠️ Nessun IP → Modalità SIMULATA.")
            self._simulated = True
            return
        try:
            print(f"🤖 Connessione a {self.robot_ip}:{self.port} ...")
            self.sock = socket.create_connection((self.robot_ip, self.port), timeout=2.0)
            self.sock.settimeout(2.0)
            print("✅ Connessione riuscita.")
        except OSError as e:
            print(f"⚠️ Errore connessione: {e}. → Modalità SIMULATA.")
            self._simulated = True

    def close(self):
        if self.sock and not self._simulated:
            try: self.sock.close()
            except OSError: pass
            print("🔌 Connessione chiusa.")

    def _send_urscript(self, script: str):
        if self._simulated or not self.sock:
            if self.verbose: print(f"(SIM) {script.strip()}")
            return
        script = script + "\n" if not script.endswith("\n") else script
        try: self.sock.sendall(script.encode("utf-8"))
        except OSError as e: print(f"⚠️ Errore invio script: {e}")

    def _send_script_file(self, filepath: str):
        if self._simulated: return
        try:
            with open(filepath, "rb") as f: data = f.read()
            self.sock.sendall(data)
        except OSError as e: print(f"⚠️ Errore file {filepath}: {e}")

    # --- MOVIMENTI ---

    def move_linear(self, pose: List[float]):
        """Movimento di precisione (cartesiano)"""
        # Protezione contro errori di formato numeri
        try:
            p = [float(x) for x in pose]
        except ValueError:
            print(f"❌ Errore coordinate non numeriche: {pose}")
            return

        cmd = (f"movel(p[{p[0]:.5f}, {p[1]:.5f}, {p[2]:.5f}, "
               f"{p[3]:.5f}, {p[4]:.5f}, {p[5]:.5f}], "
               f"a={self.max_acc}, v={self.max_speed})")
        if self.verbose: print(f"➡️ MovL: {p}")
        self._send_urscript(cmd)
        time.sleep(2.5)

    def go_home_safe(self):
        """
        USA MOVEJ (GIUNTI): Sicuro al 100% per il primo movimento.
        """
        # Rilegge config nel caso sia cambiato (opzionale) o usa self.home_joints
        if not self.home_joints or len(self.home_joints) != 6:
            # Fallback rilettura
            self.home_joints = self.config.get("robot", {}).get("home_joints")
            
        if not self.home_joints or len(self.home_joints) != 6:
            print("❌ ERRORE: 'home_joints' mancante o errato nel config.yaml!")
            return

        print("🏠 Ritorno a HOME (MoveJ Sicuro)...")
        # movej([j1, j2...], a=..., v=...)
        cmd = (f"movej([{self.home_joints[0]:.4f}, {self.home_joints[1]:.4f}, {self.home_joints[2]:.4f}, "
               f"{self.home_joints[3]:.4f}, {self.home_joints[4]:.4f}, {self.home_joints[5]:.4f}], "
               f"a={self.max_acc}, v={self.max_speed})")
        
        self._send_urscript(cmd)
        time.sleep(5.0) # Tempo abbondante per tornare a casa
        print("✅ Arrivato in Home.")

    def grip(self, close: bool):
        # Percorsi relativi corretti per Linux/Mac/Windows
        # Assicurati che i file esistano nella cartella src/
        script = "src/pinza10UR3.py" if close else "src/pinza40UR3.py"
        self._send_script_file(script)
        time.sleep(1.5)

    def _get_down_pose(self, pose_up: List[float]) -> List[float]:
        p = list(pose_up)
        p[2] += self.z_pick_offset
        return p

    # --- LOGICA GRIGLIE ---

    def get_calculated_letter_pose(self, letter: str) -> Optional[List[float]]:
        letter = letter.upper()
        for grid in self.grids_config:
            try: start, end = grid['range'].split('-')
            except: continue
            
            # Controlla se la lettera è in questo range (es. A <= C <= I)
            if start <= letter <= end:
                idx = ord(letter) - ord(start)
                cols = grid.get('cols', 4)
                pose = list(grid['base_pose'])
                
                sp_x = grid.get('spacing', {}).get('x', 0.05)
                sp_y = grid.get('spacing', {}).get('y', 0.04)
                
                # Calcolo griglia (offset)
                row = idx // cols
                col = idx % cols
                
                # Attenzione: Controlla se la tua griglia si riempie in X o Y.
                # Qui assumiamo: X=Verticale (Righe), Y=Orizzontale (Colonne)
                pose[0] += (row * sp_x) 
                pose[1] += (col * sp_y)
                
                if self.verbose: print(f"📍 '{letter}' trovata in {grid['name']}")
                return pose
                
        print(f"⚠️ Lettera '{letter}' non trovata nelle griglie.")
        return None

    def place_letter_in_calculated_slot(self, letter: str, slot_index: int):
        print(f"🤖 Pick & Place: '{letter}' -> Slot {slot_index}")
        base_slot = self.cfg_slots.get("base_pose_0")
        
        if not base_slot:
            print("❌ Errore: base_pose_0 mancante in config.")
            return

        # Calcolo Slot (Destinazione)
        slot_up = list(base_slot)
        slot_up[0] += (self.cfg_slots.get("x_step", 0.0) * slot_index)
        slot_up[1] += (self.cfg_slots.get("y_step", 0.04) * slot_index)
        slot_down = self._get_down_pose(slot_up)

        # Calcolo Lettera (Sorgente)
        src_up = self.get_calculated_letter_pose(letter)
        if not src_up: return
        src_down = self._get_down_pose(src_up)

        # --- ESECUZIONE ---
        self.go_home_safe() # 1. Casa (Sicurezza)

        # PICK
        self.grip(False)
        self.move_linear(src_up)
        self.move_linear(src_down)
        self.grip(True)
        self.move_linear(src_up)

        self.go_home_safe() # 2. Casa (Intermedio)

        # PLACE
        self.move_linear(slot_up)
        self.move_linear(slot_down)
        self.grip(False)
        self.move_linear(slot_up)
        
        self.go_home_safe() # 3. Casa (Finale)

    def remove_letter_from_slot(self, slot_index: int, letter: str):
        if letter == '_' or not letter.isalnum(): return
        print(f"🤖 Ripristino '{letter}'...")
        
        base_slot = self.cfg_slots.get("base_pose_0")
        slot_up = list(base_slot)
        slot_up[0] += (self.cfg_slots.get("x_step", 0.0) * slot_index)
        slot_up[1] += (self.cfg_slots.get("y_step", 0.04) * slot_index)
        slot_down = self._get_down_pose(slot_up)

        dest_up = self.get_calculated_letter_pose(letter)
        if not dest_up: return
        dest_down = self._get_down_pose(dest_up)

        # --- ESECUZIONE INVERSA ---
        self.go_home_safe()
        
        # PRENDI DA SLOT
        self.grip(False)
        self.move_linear(slot_up)
        self.move_linear(slot_down)
        self.grip(True)
        self.move_linear(slot_up)

        self.go_home_safe()

        # RIMETTI IN GRIGLIA
        self.move_linear(dest_up)
        self.move_linear(dest_down)
        self.grip(False)
        self.move_linear(dest_up)
        
        self.go_home_safe()

    def clear_board(self, letters: list):
        print("\n🧹 Pulizia tavolo...")
        for i in range(len(letters)-1, -1, -1):
            self.remove_letter_from_slot(i, letters[i])
        print("✨ Tavolo pulito.")