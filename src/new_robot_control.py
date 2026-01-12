import time
import socket
from typing import List, Optional

class Robot:
    """
    Controllo UR tramite socket TCP.
    Versione con HOME LINEARE (Cartesiana) per facilità di configurazione.
    """

    def __init__(self, robot_ip: str, config: dict):
        self.config = config or {}
        self.verbose = self.config.get("settings", {}).get("verbose", True)

        # --- RETE ---
        self.robot_ip = robot_ip
        self.port = self.config.get("robot", {}).get("port", 30002)
        self.sock: Optional[socket.socket] = None
        self._simulated = False

        # --- CONFIGURAZIONI ---
        safety = self.config.get("safety", {})
        self.max_speed = safety.get("speed", 0.1)
        self.max_acc = safety.get("acc", 0.2)
        self.z_pick_offset = safety.get("z_pick_offset", -0.05)
        
        # --- MODIFICA: HOME CARTESIANA ---
        # Ora leggiamo 'home_pose' invece di 'home_joints'
        self.home_pose = self.config.get("robot", {}).get("home_pose")

        # Griglie e Slot
        self.grids_config = self.config.get("grids", [])
        self.cfg_slots = self.config.get("slots", {})

        self._connect()

    def _log(self, message: str):
        if self.verbose:
            print(message)

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
            try:
                self.sock.close()
            except OSError: pass
            print("🔌 Connessione chiusa.")

    # ==========================================================
    #                 COMUNICAZIONE & MOVIMENTI
    # ==========================================================

    def _send_urscript(self, script: str):
        if self._simulated or not self.sock:
            self._log(f"(SIM) {script.strip()}")
            return
        script = script + "\n" if not script.endswith("\n") else script
        try:
            self.sock.sendall(script.encode("utf-8"))
        except OSError as e:
            print(f"⚠️ Errore invio script: {e}")

    def _send_script_file(self, filepath: str):
        if self._simulated:
            self._log(f"(SIM) File: {filepath}")
            return
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self._log(f"📄 Invio file: {filepath}")
            self.sock.sendall(data)
        except OSError as e:
            print(f"⚠️ Errore file {filepath}: {e}")

    def move_linear(self, pose: List[float], speed_factor=1.0):
        """
        Movimento lineare (cartesiano).
        speed_factor: permette di rallentare specifici movimenti (es. 0.5 = metà velocità)
        """
        speed = self.max_speed * speed_factor
        cmd = (f"movel(p[{pose[0]:.5f}, {pose[1]:.5f}, {pose[2]:.5f}, "
               f"{pose[3]:.5f}, {pose[4]:.5f}, {pose[5]:.5f}], "
               f"a={self.max_acc}, v={speed})")
        
        self._log(f"➡️ MovL: [{pose[0]:.3f}, {pose[1]:.3f}, {pose[2]:.3f}...]")
        self._send_urscript(cmd)
        time.sleep(3.0) # Movimenti lineari lunghi richiedono tempo

    def grip(self, close: bool):
        script = "src/pinza10UR3.py" if close else "src/pinza40UR3.py"
        self._log(f"{'🔴 CHIUDI' if close else '🟢 APRI'} gripper")
        self._send_script_file(script)
        time.sleep(1.5)

    def _get_down_pose(self, pose_up: List[float]) -> List[float]:
        p = list(pose_up)
        p[2] += self.z_pick_offset
        return p

    def _go_home(self):
        """
        Torna alla posizione Home usando movel (lineare).
        """
        if self.home_pose and len(self.home_pose) == 6:
            # Uso move_linear invece di move_joints
            # Rallento un po' (0.8) per sicurezza visto che è un movimento lungo
            self._log("🏠 Ritorno a Home (Lineare)...")
            self.move_linear(self.home_pose, speed_factor=0.8)
        else:
            self._log("⚠️ Home pose non definita o errata nel config.")

    # ==========================================================
    #                 LOGICA INTELLIGENTE
    # ==========================================================

    def get_calculated_letter_pose(self, letter: str) -> Optional[List[float]]:
        letter = letter.upper()
        for grid in self.grids_config:
            try:
                start_char, end_char = grid['range'].split('-')
            except ValueError:
                continue

            if start_char <= letter <= end_char:
                local_index = ord(letter) - ord(start_char)
                cols = grid.get('cols', 4)
                sp_y = grid.get('spacing', {}).get('y', 0.04)
                sp_x = grid.get('spacing', {}).get('x', 0.05)
                base_pose = grid.get('base_pose')

                if not base_pose: return None

                row = local_index // cols
                col = local_index % cols
                target_pose = list(base_pose)
                target_pose[0] += (row * sp_x) 
                target_pose[1] += (col * sp_y) 

                self._log(f"📍 Trovata '{letter}' in '{grid['name']}'")
                return target_pose
        print(f"⚠️ Errore: Lettera '{letter}' non trovata.")
        return None

    def place_letter_in_calculated_slot(self, letter: str, slot_index: int):
        if self.verbose:
            print(f"\n🚀 START: Lettera '{letter}' -> Slot {slot_index}")
        else:
            print(f"🤖 Eseguo '{letter}' -> Slot {slot_index}...")

        # 1. Calcoli
        base_slot = self.cfg_slots.get("base_pose_0")
        if not base_slot: return

        x_step = self.cfg_slots.get("x_step", 0.0)
        y_step = self.cfg_slots.get("y_step", 0.04)

        slot_pose_up = list(base_slot)
        slot_pose_up[0] += (x_step * slot_index)
        slot_pose_up[1] += (y_step * slot_index)
        slot_pose_down = self._get_down_pose(slot_pose_up)

        source_pose_up = self.get_calculated_letter_pose(letter)
        if not source_pose_up: return 
        source_pose_down = self._get_down_pose(source_pose_up)

        # 2. ESECUZIONE (Home -> Pick -> Home -> Place -> Home)
        
        self._go_home() # 🏠

        self._log("--- PICK ---")
        self.grip(False)
        self.move_linear(source_pose_up)
        self.move_linear(source_pose_down)
        self.grip(True)
        self.move_linear(source_pose_up)

        self._go_home() # 🏠 Passaggio sicuro

        self._log("--- PLACE ---")
        self.move_linear(slot_pose_up)
        self.move_linear(slot_pose_down)
        self.grip(False)
        self.move_linear(slot_pose_up)
        
        self._go_home() # 🏠
        self._log("✅ Fatto.")

    def remove_letter_from_slot(self, slot_index: int, letter: str):
        if letter == '_' or not letter.strip() or not letter.isalnum():
            return

        print(f"🤖 Ripristino '{letter}' dallo Slot {slot_index}...")

        # 1. Calcoli
        base_slot = self.cfg_slots.get("base_pose_0")
        x_step = self.cfg_slots.get("x_step", 0.0)
        y_step = self.cfg_slots.get("y_step", 0.04)
        
        slot_pose_up = list(base_slot)
        slot_pose_up[0] += (x_step * slot_index)
        slot_pose_up[1] += (y_step * slot_index)
        slot_pose_down = self._get_down_pose(slot_pose_up)

        origin_pose_up = self.get_calculated_letter_pose(letter)
        if not origin_pose_up: return
        origin_pose_down = self._get_down_pose(origin_pose_up)

        # 2. ESECUZIONE
        self._go_home() # 🏠

        self._log("--- PICK (da Slot) ---")
        self.grip(False)
        self.move_linear(slot_pose_up)
        self.move_linear(slot_pose_down)
        self.grip(True)
        self.move_linear(slot_pose_up)
        
        self._go_home() # 🏠

        self._log("--- PLACE (su Griglia) ---")
        self.move_linear(origin_pose_up)
        self.move_linear(origin_pose_down)
        self.grip(False)
        self.move_linear(origin_pose_up)
        
        self._go_home() # 🏠
        self._log(f"✅ Lettera rimessa a posto.")

    def clear_board(self, current_board_letters: list):
        print("\n🧹 PULIZIA TAVOLO...")
        for i in range(len(current_board_letters) - 1, -1, -1):
            letter = current_board_letters[i]
            if letter != '_' and letter.isalnum():
                self.remove_letter_from_slot(i, letter)
        self._go_home()
        print("✨ Tavolo pulito.")