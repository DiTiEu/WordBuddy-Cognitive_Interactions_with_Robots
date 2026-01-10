import time
import socket
from typing import List, Optional

class Robot:
    """
    Controllo UR tramite socket TCP.
    Include gestione log 'verbose' per nascondere i messaggi di debug.
    """

    def __init__(self, robot_ip: str, config: dict):
        self.config = config or {}
        
        # --- 0. IMPOSTAZIONI LOG (NUOVO) ---
        # Se True, stampa tutto. Se False, stampa solo errori e avvisi importanti.
        self.verbose = self.config.get("settings", {}).get("verbose", True)

        # --- 1. CONFIGURAZIONE RETE ---
        self.robot_ip = robot_ip
        self.port = self.config.get("robot", {}).get("port", 30002)
        self.sock: Optional[socket.socket] = None
        self._simulated = False

        # --- 2. CONFIGURAZIONE MOVIMENTO & SICUREZZA ---
        safety = self.config.get("safety", {})
        self.max_speed = safety.get("speed", 0.1)
        self.max_acc = safety.get("acc", 0.2)
        self.safe_height = safety.get("safe_height", 0.25)
        self.z_pick_offset = safety.get("z_pick_offset", -0.05)

        # --- 3. CONFIGURAZIONE GRIGLIA & SLOT ---
        self.cfg_grid = self.config.get("grid", {})
        self.cfg_slots = self.config.get("slots", {})

        # --- 4. CONNESSIONE ---
        self._connect()

    def _log(self, message: str):
        """Stampa messaggi solo se la modalità verbose è attiva."""
        if self.verbose:
            print(message)

    def _connect(self):
        """Gestisce la connessione al socket."""
        if not self.robot_ip:
            print("⚠️ Nessun IP specificato → Modalità SIMULATA.") # Sempre visibile
            self._simulated = True
            return

        try:
            print(f"🤖 Connessione a {self.robot_ip}:{self.port} ...") # Sempre visibile
            self.sock = socket.create_connection((self.robot_ip, self.port), timeout=2.0)
            self.sock.settimeout(2.0)
            print("✅ Connessione riuscita.") # Sempre visibile
        except OSError as e:
            print(f"⚠️ Errore connessione: {e}. → Modalità SIMULATA.") # Sempre visibile errori
            self._simulated = True

    def close(self):
        if self.sock and not self._simulated:
            try:
                self.sock.close()
            except OSError:
                pass
            print("🔌 Connessione chiusa.") # Sempre visibile

    # ==========================================================
    #                 COMUNICAZIONE & BASSI LIVELLI
    # ==========================================================

    def _send_urscript(self, script: str):
        if self._simulated or not self.sock:
            self._log(f"(SIM) {script.strip()}") # DEBUG
            return
        
        script = script if script.endswith("\n") else script + "\n"
        try:
            self.sock.sendall(script.encode("utf-8"))
        except OSError as e:
            print(f"⚠️ Errore invio script: {e}") # ERRORE

    def _send_script_file(self, filepath: str):
        if self._simulated:
            self._log(f"(SIM) Eseguo file: {filepath}") # DEBUG
            return
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self._log(f"📄 Invio file: {filepath}") # DEBUG
            self.sock.sendall(data)
        except OSError as e:
            print(f"⚠️ Errore lettura/invio file {filepath}: {e}") # ERRORE

    # ==========================================================
    #                     MOVIMENTI BASE
    # ==========================================================

    def move_linear(self, pose: List[float]):
        cmd = (f"movel(p[{pose[0]:.5f}, {pose[1]:.5f}, {pose[2]:.5f}, "
               f"{pose[3]:.5f}, {pose[4]:.5f}, {pose[5]:.5f}], "
               f"a={self.max_acc}, v={self.max_speed})")
        
        # Usa _log invece di print per nascondere se non necessario
        self._log(f"➡️ Linear a: [{pose[0]:.3f}, {pose[1]:.3f}, {pose[2]:.3f}...]")
        self._send_urscript(cmd)
        time.sleep(2.5)

    def grip(self, close: bool):
        """True = Chiudi (Presa), False = Apri (Rilascio)"""
        script = "src/pinza10UR3.py" if close else "src/pinza40UR3.py"
        action = "🔴 CHIUDI" if close else "🟢 APRI"
        
        self._log(f"{action} gripper") # DEBUG
        self._send_script_file(script)
        time.sleep(1.5)

    def _get_down_pose(self, pose_up: List[float]) -> List[float]:
        pose_down = list(pose_up)
        pose_down[2] += self.z_pick_offset
        return pose_down

    # ==========================================================
    #                 LOGICA COGNITIVA (CALCOLI)
    # ==========================================================

    def get_calculated_letter_pose(self, letter: str) -> Optional[List[float]]:
        # 1. Recupero Config
        base_pose = self.cfg_grid.get("base_pose_A")
        if not base_pose:
            print("⚠️ Errore Config: 'base_pose_A' mancante.") # ERRORE
            return None
            
        col_spacing = self.cfg_grid.get("col_spacing", 0.04)
        row_spacing = self.cfg_grid.get("row_spacing", 0.05)
        cols_per_row = self.cfg_grid.get("cols_per_row", 4)

        # 2. Calcolo
        letter = letter.upper()
        index = ord(letter) - ord('A')
        
        if index < 0 or index > 25:
            print(f"⚠️ Lettera '{letter}' non supportata.") # ERRORE
            return None

        row_index = index // cols_per_row
        col_index = index % cols_per_row

        # 3. Offset
        target_pose = list(base_pose)
        target_pose[0] += (row_index * row_spacing)
        target_pose[1] += (col_index * col_spacing)

        self._log(f"🧮 Griglia '{letter}': Riga {row_index}, Col {col_index}") # DEBUG
        return target_pose

    def place_letter_in_calculated_slot(self, letter: str, slot_index: int):
        # Messaggio di inizio operazione (questo è utile lasciarlo o metterlo in log?)
        # Lo mettiamo in print normale perché è un'azione principale, ma togliamo i dettagli.
        if self.verbose:
            print(f"\n🚀 START: Lettera '{letter}' -> Slot {slot_index}")
        else:
            # Se siamo silenziosi, magari un mini feedback serve comunque
            print(f"🤖 Sposto '{letter}' su Slot {slot_index}...")

        # --- A. CALCOLO SLOT ---
        base_slot = self.cfg_slots.get("base_pose_0")
        if not base_slot:
            print("⚠️ Errore Config: 'base_pose_0' mancante.")
            return

        x_step = self.cfg_slots.get("x_step", 0.0)
        y_step = self.cfg_slots.get("y_step", 0.04)

        slot_pose_up = list(base_slot)
        slot_pose_up[0] += (x_step * slot_index)
        slot_pose_up[1] += (y_step * slot_index)
        slot_pose_down = self._get_down_pose(slot_pose_up)

        # --- B. CALCOLO LETTERA ---
        source_pose_up = self.get_calculated_letter_pose(letter)
        if not source_pose_up:
            return
        source_pose_down = self._get_down_pose(source_pose_up)

        # --- C. ESECUZIONE ---
        self._log("--- FASE PICK ---")
        self.grip(False)
        self.move_linear(source_pose_up)
        self.move_linear(source_pose_down)
        self.grip(True)
        self.move_linear(source_pose_up)

        self._log("--- FASE PLACE ---")
        self.move_linear(slot_pose_up)
        self.move_linear(slot_pose_down)
        self.grip(False)
        self.move_linear(slot_pose_up)

        self._log("✅ Sequenza completata.")

    def remove_letter_from_slot(self, slot_index: int):
        print(f"🤖 Rimuovo lettera da Slot {slot_index}...") # Feedback utente base
        
        base_slot = self.cfg_slots.get("base_pose_0")
        x_step = self.cfg_slots.get("x_step", 0.0)
        y_step = self.cfg_slots.get("y_step", 0.04)
        
        slot_pose_up = list(base_slot)
        slot_pose_up[0] += (x_step * slot_index)
        slot_pose_up[1] += (y_step * slot_index)
        slot_pose_down = self._get_down_pose(slot_pose_up)

        discard_pose = list(base_slot)
        discard_pose[0] += 0.15 
        discard_pose[2] += 0.05 
        
        self._log(f"🗑️ Rimozione in corso...")
        self.grip(False)
        self.move_linear(slot_pose_up)
        self.move_linear(slot_pose_down)
        self.grip(True)
        self.move_linear(slot_pose_up)
        
        self.move_linear(discard_pose)
        self.grip(False)
        self._log(f"✅ Slot {slot_index} liberato.")

    def clear_board(self, num_slots: int):
        print("\n🧹 Pulizia tavolo...")
        for i in range(num_slots):
            # Qui non serve printare ogni rimozione se verbose è False, 
            # remove_letter_from_slot ha già il suo print base.
            self.remove_letter_from_slot(i)
        print("✨ Tavolo pulito.")