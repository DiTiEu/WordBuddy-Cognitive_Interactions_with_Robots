from robot_control import Robot
from utils import load_config
import time

config = load_config("data/config.yaml")
robot = Robot(config["robot_ip"], config["poses"], config["safety"])

# 1) Test connessione: mostra un popup sul pendant
robot._send_urscript('popup("Test connessione da PC", title="PC → UR3", warning=False)')
time.sleep(1.0)

# 2) Se vedi il popup, prova il gripper
input("Se hai visto il popup sul pendant, premi INVIO per testare il gripper...")

robot.grip(False)   # apri
time.sleep(1.0)
robot.grip(True)    # chiudi

robot.close()
