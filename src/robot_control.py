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