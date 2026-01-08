# src/robot_control.py

import time
import socket
from typing import List
import os

class Robot:
    """
    Controllo UR tramite socket TCP sulla porta 30002.
    """

    def __init__(self, robot_ip: str, poses: dict, safety: dict, port: int = 30002):
        self.robot_ip = robot_ip
        self.port = port

        self.poses = poses or {}
        self.letter_sources = self.poses.get("letter_sources", {})
        self.slots = self.poses.get("slots", {})

        self.safe_height = safety.get("safe_height", 0.25)
        # z_pick_offset: quanto scendere rispetto alla posa salvata (es. -0.05)
        self.z_pick_offset = safety.get("z_pick_offset", -0.05) 
        self.max_speed = safety.get("max_speed", 0.1)
        self.max_acc = safety.get("max_acc", 0.2)

        self._simulated = False
        self.sock: socket.socket | None = None

        if self.robot_ip is None:
            print("⚠️ Nessun IP robot specificato → modalità SIMULATA.")
            self._simulated = True
            return

        try:
            print(f"🤖 Connessione all'UR3 {self.robot_ip}:{self.port} ...")
            self.sock = socket.create_connection((self.robot_ip, self.port), timeout=2.0)
            self.sock.settimeout(2.0)
            print("✅ Connessione socket riuscita.")
        except OSError as e:
            print(f"⚠️ Impossibile connettersi a {self.robot_ip}:{self.port} → {e}")
            print("➡️ Passo alla modalità SIMULATA.")
            self._simulated = True
            self.sock = None

    def close(self):
        if self.sock is not None and not self._simulated:
            try:
                self.sock.close()
            except OSError:
                pass
            print("🔌 Connessione socket chiusa.")

    def _send_urscript(self, script: str):
        if self._simulated or self.sock is None:
            print(f"(SIM) URScript:\n{script.strip()}")
            return
        if not script.endswith("\n"):
            script += "\n"
        try:
            self.sock.sendall(script.encode("utf-8"))
        except OSError as e:
            print(f"⚠️ Errore nell'invio di URScript: {e}")

    def _send_script_file(self, filepath: str):
        if self._simulated or self.sock is None:
            print(f"(SIM) Invierei il file URScript: {filepath}")
            return
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            print(f"📄 Invio script UR: {filepath} ({len(data)} bytes)")
            self.sock.sendall(data)
        except OSError as e:
            print(f"⚠️ Errore nel leggere o inviare {filepath}: {e}")

    # ---------- MOVIMENTO BASE ----------

    def move_joints(self, joints: List[float]):
        cmd = (
            f"movej([{joints[0]:.5f}, {joints[1]:.5f}, {joints[2]:.5f}, "
            f"{joints[3]:.5f}, {joints[4]:.5f}, {joints[5]:.5f}], "
            f"a={self.max_acc}, v={self.max_speed})"
        )
        print("➡️ move_joints:", joints)
        self._send_urscript(cmd)
        time.sleep(2.0)

    def move_linear(self, pose: List[float]):
        """Movimento lineare verso una posa assoluta [x,y,z,rx,ry,rz]."""
        cmd = (
            f"movel(p[{pose[0]:.5f}, {pose[1]:.5f}, {pose[2]:.5f}, "
            f"{pose[3]:.5f}, {pose[4]:.5f}, {pose[5]:.5f}], "
            f"a={self.max_acc}, v={self.max_speed})"
        )
        print(f"➡️ move_linear verso: {pose}")
        self._send_urscript(cmd)
        time.sleep(2.5) 

    def grip(self, state: bool):
        """True -> CHIUDI, False -> APRI"""
        # Assicurati che i file siano nella cartella corretta o usa percorso assoluto/relativo
        script_apri = "src\pinza40UR3.py"
        script_chiudi = "src\pinza10UR3.py"
        
        filepath = script_chiudi if state else script_apri
        print(f"{'🔴 CHIUDI' if state else '🟢 APRI'} gripper ({filepath})")
        self._send_script_file(filepath)
        time.sleep(1.5)

    # ---------- UTILS CALCOLO POSIZIONE ----------

    def _get_down_pose(self, pose: List[float]) -> List[float]:
        """
        Prende una posa [x,y,z,rx,ry,rz] e restituisce una NUOVA posa
        con la Z modificata sommando z_pick_offset.
        Non interroga il robot, fa solo matematica pura.
        """
        # Creiamo una copia della lista per non modificare l'originale
        down_pose = list(pose)
        
        # Modifichiamo la Z (indice 2)
        # z_pick_offset nel config deve essere negativo (es. -0.05)
        down_pose[2] = down_pose[2] + self.z_pick_offset
        
        return down_pose

    # ---------- PICK & PLACE LOGIC ----------

    def place_letter_in_slot(self, letter: str, slot_index: int):
        """
        Esegue Pick & Place calcolando le coordinate di discesa
        basandosi ESCLUSIVAMENTE sui dati del config.yaml.
        Nessuna chiamata a get_actual_tcp_pose().
        """
        print(f"\n📦 INIZIO Pick&Place: Lettera '{letter}' -> Slot {slot_index}")
        
        # --- 0. RECUPERO COORDINATE DAL CONFIG ---
        letter = letter.upper()
        if letter not in self.letter_sources:
            print(f"⚠️ Errore: Lettera {letter} non trovata nei source.")
            return
        
        slot_key = str(slot_index)
        if slot_key not in self.slots:
            print(f"⚠️ Errore: Slot {slot_index} non trovato.")
            return

        # Posa ALTA della lettera (dal config)
        source_pose_up = self.letter_sources[letter]
        # Calcolo Posa BASSA della lettera (matematica Python)
        source_pose_down = self._get_down_pose(source_pose_up)

        # Posa ALTA dello slot (dal config)
        slot_pose_up = self.slots[slot_key]
        # Calcolo Posa BASSA dello slot (matematica Python)
        slot_pose_down = self._get_down_pose(slot_pose_up)


        # --- FASE 1: PICK (PRESA) ---
        print("--- FASE PICK ---")
        
        self.grip(False)                    # 1. Apri
        self.move_linear(source_pose_up)    # 2. Vai sopra la lettera (ALTO)
        
        print(f"   ⬇️ Scendo a Z={source_pose_down[2]:.4f}")
        self.move_linear(source_pose_down)  # 3. Scendi alla posa calcolata (BASSO)
        
        self.grip(True)                     # 4. Chiudi (PRESA)
        
        print(f"   ⬆️ Risalgo a Z={source_pose_up[2]:.4f}")
        self.move_linear(source_pose_up)    # 5. Torna su (ALTO)


        # --- FASE 2: PLACE (DEPOSITO) ---
        print("--- FASE PLACE ---")
        
        self.move_linear(slot_pose_up)      # 6. Vai sopra lo slot (ALTO)
        
        print(f"   ⬇️ Scendo a Z={slot_pose_down[2]:.4f}")
        self.move_linear(slot_pose_down)    # 7. Scendi alla posa calcolata (BASSO)
        
        self.grip(False)                    # 8. Apri (RILASCIO)
        
        print(f"   ⬆️ Risalgo a Z={slot_pose_up[2]:.4f}")
        self.move_linear(slot_pose_up)      # 9. Torna su (ALTO)

        print("✅ Sequenza completata.\n")

    def get_calculated_letter_pose(self, letter: str):
        """
        HELPER: Calcola la posa di una lettera (A-T) basandosi su una griglia 4x5.
        """
        # --- CONFIGURAZIONE GRIGLIA LETTERE ---
        # Coordinata esatta della lettera 'A' (da te fornita)
        base_pose_A = [0.310, 0.097, 0.037, 0.007, 3.13, 0.006]
        
        col_spacing = 0.04  # 4 cm Orizzontale (Y)
        row_spacing = 0.05  # 5 cm Verticale (X)
        cols_per_row = 4    # 4 lettere per riga

        letter = letter.upper()
        index = ord(letter) - ord('A') # A=0, B=1...

        # Controllo sicurezza (A-T)
        if index < 0 or index > 19:
            print(f"⚠️ Errore: Lettera '{letter}' fuori dalla griglia supportata (A-T).")
            return None

        # Calcolo riga e colonna
        row_index = index // cols_per_row
        col_index = index % cols_per_row

        # Calcolo coordinate
        target_pose = list(base_pose_A)
        target_pose[0] += (row_index * row_spacing) # Offset X (Righe)
        target_pose[1] += (col_index * col_spacing) # Offset Y (Colonne)
        
        return target_pose

    def place_letter_in_calculated_slot(self, letter: str, slot_index: int):
        """
        Esegue Pick & Place COMPLETAMENTE CALCOLATO.
        PICK: Calcolato su griglia 4x5 (tramite get_calculated_letter_pose).
        PLACE: Calcolato su linea orizzontale (Slot 0 + offset).
        """
        print(f"\n🧮 INIZIO Pick&Place Full-Math: Lettera '{letter}' -> Slot {slot_index}")

        # --- 0. CALCOLO POSA SLOT (DESTINAZIONE) ---
        # Coordinata base dello Slot 0 [X, Y, Z, Rx, Ry, Rz]
        slot_0_pose = [0.385, -0.250, 0.047, 0.007, 3.13, 0.006]
        
        # Calcolo Offset Slot (4 cm a destra per ogni indice)
        y_offset_slot = 0.04 * slot_index 
        
        slot_pose_up = list(slot_0_pose)
        slot_pose_up[1] = slot_0_pose[1] + y_offset_slot # Aggiungo offset a Y

        slot_pose_down = self._get_down_pose(slot_pose_up)


        # --- 1. CALCOLO POSA LETTERA (SORGENTE) ---
        # Qui chiamiamo la nuova funzione invece di leggere self.letter_sources
        source_pose_up = self.get_calculated_letter_pose(letter)

        if source_pose_up is None:
            return # Interrompe se la lettera non è valida

        source_pose_down = self._get_down_pose(source_pose_up)


        # --- 2. ESECUZIONE FISICA (Invariata) ---
        
        # --- FASE PICK ---
        print(f"--- FASE PICK (Lettera {letter}) ---")
        print(f"   📍 Coord Pick calcolate: X={source_pose_up[0]:.3f}, Y={source_pose_up[1]:.3f}")

        self.grip(False)
        self.move_linear(source_pose_up)    # Vai sopra la lettera
        
        print(f"   ⬇️ Scendo")
        self.move_linear(source_pose_down)  # Scendi
        self.grip(True)                     # Prendi
        
        print(f"   ⬆️ Risalgo")
        self.move_linear(source_pose_up)    # Sali

        # --- FASE PLACE ---
        print(f"--- FASE PLACE (Slot {slot_index}) ---")
        print(f"   📍 Coord Place calcolate: Y={slot_pose_up[1]:.3f}")
        
        self.move_linear(slot_pose_up)      # Vai sopra lo slot
        
        print(f"   ⬇️ Scendo")
        self.move_linear(slot_pose_down)    # Scendi
        self.grip(False)                    # Rilascia
        
        print(f"   ⬆️ Risalgo")
        self.move_linear(slot_pose_up)      # Sali

        print("✅ Sequenza completata.\n")