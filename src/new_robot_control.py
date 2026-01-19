import time
import socket
from typing import List, Optional

class Robot:
    """
    Universal Robots control via TCP socket.
    Updated version to handle configuration and safe Home positioning (MoveJ).
    """

    def __init__(self, robot_ip: str, config: dict):
        self.config = config or {}
        self.verbose = self.config.get("settings", {}).get("verbose", False)
        
        # --- Network ---
        self.robot_ip = robot_ip
        self.port = self.config.get("robot", {}).get("port", 30002)
        self.sock: Optional[socket.socket] = None
        self._simulated = False

        # --- Parameters ---
        safety = self.config.get("safety", {})
        self.max_speed = safety.get("speed", 0.1)
        self.max_acc = safety.get("acc", 0.2)
        self.z_pick_offset = safety.get("z_pick_offset", -0.05)
        self.home_joints = self.config.get("robot", {}).get("home_joints")

        self.grids_config = self.config.get("grids", [])
        self.cfg_slots = self.config.get("slots", {})

        self._connect()

    def _connect(self):
        """Connects to the robot or sets simulated mode if no IP is provided."""
        if not self.robot_ip:
            print("⚠️ No IP provided -> SIMULATED mode.")
            self._simulated = True
            return
        try:
            print(f"🤖 Connecting to {self.robot_ip}:{self.port}...")
            self.sock = socket.create_connection((self.robot_ip, self.port), timeout=2.0)
            print("✅ Connection successful.")
        except OSError as e:
            print(f"⚠️ Connection error: {e} -> SIMULATED mode.")
            self._simulated = True

    def close(self):
        """Closes the socket connection."""
        if self.sock and not self._simulated:
            self.sock.close()
            print("🔌 Connection closed.")

    def _send_urscript(self, script: str):
        """Sends URScript commands to the robot."""
        if self._simulated or not self.sock:
            if self.verbose: print(f"(SIM) {script.strip()}")
            return
        self.sock.sendall((script + "\n").encode("utf-8"))

    def _send_script_file(self, filepath: str):
        """Sends a script file content to the robot."""
        if self._simulated: return
        try:
            with open(filepath, "rb") as f: data = f.read()
            self.sock.sendall(data)
        except OSError as e: print(f"⚠️ Error with file {filepath}: {e}")

    def move_linear(self, pose: List[float]):
        """Precision Cartesian movement (movel)."""
        cmd = f"movel(p[{pose[0]}, {pose[1]}, {pose[2]}, {pose[3]}, {pose[4]}, {pose[5]}], a={self.max_acc}, v={self.max_speed})"
        if self.verbose: print(f"➡️ MovL: {pose}")
        self._send_urscript(cmd)
        time.sleep(2.5)

    def go_home_safe(self):
        """Returns to HOME using MoveJ (Joints) for maximum safety."""
        if not self.home_joints:
            print("❌ ERROR: 'home_joints' missing in configuration!")
            return
        print("🏠 Returning HOME (Safe MoveJ)...")
        cmd = f"movej({self.home_joints}, a={self.max_acc}, v={self.max_speed})"
        self._send_urscript(cmd)
        time.sleep(4.0)

    def grip(self, close: bool):
        """Opens or closes the gripper by sending specific script files."""
        script = "src/pinza10UR3.py" if close else "src/pinza40UR3.py"
        self._send_script_file(script)
        time.sleep(1.5)

    def _get_down_pose(self, pose_up: List[float]) -> List[float]:
        """Calculates the lowered Z position for picking/placing."""
        p = list(pose_up)
        p[2] += self.z_pick_offset
        return p

    def get_calculated_letter_pose(self, letter: str) -> Optional[List[float]]:
        """Finds the coordinates for a letter in the storage grids."""
        letter = letter.upper()
        for grid in self.grids_config:
            try: start, end = grid['range'].split('-')
            except: continue
            
            if start <= letter <= end:
                idx = ord(letter) - ord(start)
                cols = grid.get('cols', 4)
                pose = list(grid['base_pose'])
                sp_x = grid.get('spacing', {}).get('x', 0.05)
                sp_y = grid.get('spacing', {}).get('y', 0.04)
                
                row = idx // cols
                col = idx % cols
                
                pose[0] += (row * sp_x)
                pose[1] += (col * sp_y)
                return pose
        return None

    def place_letter_in_calculated_slot(self, letter: str, slot_index: int):
        """Picks a letter from the grid and places it into a board slot."""
        print(f"🤖 Action: Picking '{letter}' -> Placing in Slot {slot_index}")
        base_slot = self.cfg_slots.get("base_pose_0")
        if not base_slot: return

        # Calculate Slot (Destination)
        slot_up = list(base_slot)
        slot_up[0] += (self.cfg_slots.get("x_step", 0.0) * slot_index)
        slot_up[1] += (self.cfg_slots.get("y_step", 0.04) * slot_index)
        slot_down = self._get_down_pose(slot_up)

        # Calculate Letter (Source)
        src_up = self.get_calculated_letter_pose(letter)
        if not src_up: return
        src_down = self._get_down_pose(src_up)

        # Execution
        self.go_home_safe()
        self.grip(False)
        self.move_linear(src_up)
        self.move_linear(src_down)
        self.grip(True)
        self.move_linear(src_up)
        self.go_home_safe()
        self.move_linear(slot_up)
        self.move_linear(slot_down)
        self.grip(False)
        self.move_linear(slot_up)
        self.go_home_safe()

    def remove_letter_from_slot(self, slot_index: int, letter: str):
        """Restores a letter from a board slot back to the grid."""
        if letter == '_' or not letter.isalnum(): return
        print(f"🤖 Action: Restoring '{letter}' from Slot {slot_index} to grid...")
        
        base_slot = self.cfg_slots.get("base_pose_0")
        slot_up = list(base_slot)
        slot_up[0] += (self.cfg_slots.get("x_step", 0.0) * slot_index)
        slot_up[1] += (self.cfg_slots.get("y_step", 0.04) * slot_index)
        slot_down = self._get_down_pose(slot_up)

        dest_up = self.get_calculated_letter_pose(letter)
        if not dest_up: return
        dest_down = self._get_down_pose(dest_up)

        self.go_home_safe()
        self.grip(False)
        self.move_linear(slot_up)
        self.move_linear(slot_down)
        self.grip(True)
        self.move_linear(slot_up)
        self.go_home_safe()
        self.move_linear(dest_up)
        self.move_linear(dest_down)
        self.grip(False)
        self.move_linear(dest_up)
        self.go_home_safe()

    def clear_board(self, letters: list):
        """Clears all letters from the board slots."""
        print("\n🧹 Cleaning table...")
        for i in range(len(letters)-1, -1, -1):
            self.remove_letter_from_slot(i, letters[i])
        print("✨ Table cleaned.")