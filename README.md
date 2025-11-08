# WordBuddy – Interactive Educational Robot

**WordBuddy** is an interactive robot that helps learners practice word recognition and spelling with physical letter blocks.  
It combines **computer vision** for letter detection, **robot motion** (UR3/UR3e) for setting up the task, and **Text-to-Speech (TTS)** for guidance and feedback.

This repository contains the Python code, data, and documentation to run a minimal yet well-structured MVP: a basic pick-and-place to lay out partial words, user completion on the table, vision verification, and voice feedback.

> **Status:** MVP in progress – structured code, initial motion & assets ready; vision and evaluation plan under active development.

---

## Key Design (Current Setup)

- **Robot Motion:** Programs recorded on the **UR3/UR3e** using **pedal + free-drive** to save waypoints.  
  Python communicates with the robot via **TCP/IP** using URScript or `urx` for moves and gripper control.
- **Computer Vision:** Overhead camera + **OpenCV** (+ **Tesseract OCR**) for letter recognition.  
  **ArUco markers** define the table frame and scale.
- **Interaction:** **TTS** guides the session; simple success or encouragement phrases.
- **Architecture:** Pure **Python**, no ROS. Modules communicate through function calls, managed by `main.py`.

---

## Project Structure

```
WordBuddy/
│
├── src/                        
│   ├── main.py                 
│   ├── vision.py               # Letter recognition (OCR + calibration)
│   ├── robot_control.py        # Robot control (movements, pick & place)
│   ├── game_logic.py           # Game logic (word management, completion verification)
│   ├── tts_module.py           # Text-to-speech synthesis (TTS feedback)
│   └── utils.py                # Utility functions (logging, configurations)
│
├── data/                       
│   ├── words.json              # Predefined words for the game
│   ├── config.yaml             # General configurations (table dimensions, safety)
│   ├── calibration/            # Camera calibration data (ArUco files)
│   └── test_logs/              # Test execution logs (successes, errors, timings)
│
├── hardware/                    # Physical project materials
│   ├── blocks/                 # Photos of letter blocks (high readability)
│   ├── markers/                # ArUco markers for table calibration
│   └── camera/                 # Fixed camera photos and configuration
│
├── docs/                        # Documentation
│   ├── requirements.md         # Functional and non-functional requirements
│   ├── design.md               # System architecture description
│   ├── benchmarking.md         # Benchmarking results with other solutions
│   ├── evaluation_plan.md      # Testing plan and evaluation methods
│   └── presentation.md         # Presentation draft
│
├── reports/                    
│   ├── initial_report.md     
│   └── final_report.md         
│
└── README.md                    
```

---

## Technologies

- **UR3/UR3e** – Robotic arm (pick & place, free-drive, pedal)
- **Python 3.10+**
- **OpenCV** – Image processing and marker detection
- **Tesseract OCR** – Optical character recognition for letter blocks
- **pyttsx3 / gTTS** – Text-to-Speech for voice feedback
- **`urx` / RTDE** – TCP/IP communication with the UR3 robot
- **VS Code** – Development environment

---

## Quick Start

### 1️ Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate         # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt

(Make sure Tesseract OCR is installed on your system)
