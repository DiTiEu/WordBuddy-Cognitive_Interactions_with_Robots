from utils import load_config
from robot_control import Robot
import time
import os

if __name__ == "__main__":
    # Carica config
    config = load_config("data/config.yaml")

    # Inizializza robot
    robot = Robot(
        robot_ip=config.get("robot_ip"),
        poses=config.get("poses", {}),
        safety=config.get("safety", {})
    )

    # (opzionale) vai in home se definita
    if "home" in config.get("poses", {}):
        print("➡️ Vado in pose 'home'")
        robot.move_joints(config["poses"]["home"])
        time.sleep(1.0)

    print(">>> TEST GRIPPER: APRI → CHIUDI <<<")

    # APRI
    robot.grip(False)
    time.sleep(2.0)

    # CHIUDI
    robot.grip(True)
    time.sleep(2.0)

    # di nuovo APRI
    robot.grip(False)
    time.sleep(2.0)

    robot.close()
    print("✅ Test gripper terminato.")
