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

The project is organized into the following directories:

