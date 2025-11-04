# WordBuddy - Interactive Educational Robot

WordBuddy is an interactive robot designed to help children and learners improve their word recognition and spelling skills through a hands-on game. The robot uses a combination of **vision** for letter recognition, **robot motion** for feedback and word formation, and **Text-to-Speech (TTS)** for auditory interaction. The main objective of this project is to create an engaging and educational experience that integrates robotics and AI technologies.

## Project Overview

The system consists of the following main components:
- **Robot Control**: A UR3/UR3e robot is used to pick and place blocks in the correct order, forming words and interacting with users.
- **Computer Vision**: Using OpenCV and OCR (Tesseract), the robot detects and recognizes letters from physical blocks on the table.
- **Text-to-Speech (TTS)**: The robot provides auditory feedback to guide users, using Python libraries like pyttsx3.
- **Human-Robot Interaction (HRI)**: The robot engages users with simple gestures and vocal encouragement, creating an interactive and motivating learning environment.

## Technologies Used

- **UR3/UR3e Robot**: For the physical manipulation of blocks and movement.
- **Python**: Main language for all programming and robot control.
- **OpenCV**: For camera capture and image processing, including letter detection and OCR.
- **Tesseract OCR**: For optical character recognition (OCR) to read letters from blocks.
- **pyttsx3 / gTTS**: For Text-to-Speech conversion, providing vocal feedback.
- **ArUco markers**: For camera calibration and table positioning.

## Project Structure

```
WordBuddy/
│
├── src/                     # Source code for the robot and interactions
│   ├── main.py              # Main entry point, handles game flow
│   ├── vision.py            # Letter recognition via OpenCV and OCR
│   ├── robot_control.py     # Robot control logic (pick & place, gestures)
│   ├── game_logic.py        # Logic for word selection, verification
│   ├── tts_module.py        # Text-to-speech module for feedback
│   └── utils.py             # Utility functions for logging, configurations
│
├── data/                    # Data assets for the project
│   ├── words.json           # List of words for the game
│   ├── config.yaml          # Configuration file for system settings
│   ├── calibration/         # Calibration data for camera (ArUco markers)
│   └── test_logs/           # Logs from tests (success, errors, times)
│
├── hardware/                # Physical setup and hardware-related files
│   ├── blocks/              # Photos of letter blocks
│   ├── markers/             # ArUco markers for table calibration
│   └── camera/              # Camera setup and configuration images
│
├── docs/                    # Documentation related to the project
│   ├── requirements.md      # Functional and non-functional requirements
│   ├── design.md            # Architecture and system design
│   ├── benchmarking.md      # Benchmarking and comparison with similar projects
│   ├── evaluation_plan.md   # Plan for testing and evaluation
│   └── presentation.md      # Initial presentation materials
│
├── reports/                 # Reports and presentations
│   ├── initial_report.md    # Draft of the project report
│   ├── final_report.md      # Final report after the project completion
│   └── slides/              # Presentation slides
│
└── README.md                # This file
```
```


## How to Run

### Prerequisites
- Python 3.x
- Required libraries:
  - `opencv-python`
  - `pyttsx3` or `gTTS`
  - `tesseract`
  - `urx` (for UR3 robot control)

Install the necessary dependencies:

pip install -r requirements.txt


### Running the Game
1. Ensure the robot is connected and ready.
2. Set up the camera with ArUco markers for calibration.
3. Run the main program:

python src/main.py

4. The robot will prompt you with a word, and you will interact by placing the correct letters to complete the word.

## Contributing

Feel free to contribute to the project by opening issues or submitting pull requests. Contributions can include:
- Bug fixes
- Enhancements in robot control or vision
- Improvements in user interaction and feedback

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- **UR3e Robot** for their incredible robotic arm capabilities.
- **OpenCV** and **Tesseract** for vision and OCR.
- **pyttsx3** for seamless Text-to-Speech capabilities.

---

## Contact

For any inquiries or to contribute to the project, feel free to reach out to:
- Email: (mailto:your.email@example.com)
- GitHub: (https://github.com/yourusername)

