# Humaniod_robot
Overview

This project is a voice-controlled humanoid robot built using the LEGO EV3 platform.
It integrates robotics, AI, networking, and voice recognition to allow natural language control of a humanoid robot.

The robot can be controlled using:

GUI buttons

Voice commands

AI-powered natural language input

Technologies Used

Python

Tkinter GUI

Google Speech Recognition

Google Gemini API

Fuzzy Matching (FuzzyWuzzy)

TCP Socket Networking

EV3DEV2 Robotics Library

System Architecture

Client (Laptop)
↓
TCP Socket Communication
↓
EV3 Server
↓
Motor Control + Sensor Feedback

Features
Robot Movements

Walk Forward / Backward

Turn Left / Right

Slide Movement

Autonomous Obstacle Avoidance

Hand Gestures

Raise Hands

Lower Hands

Wave Left Hand

Wave Right Hand

Punch Action

Voice Interaction

Manual Voice Command

Continuous Listening Mode

AI Intent Recognition using Gemini

Sensors

Ultrasonic distance measurement

Obstacle detection

GUI Features

Control panel

Chat-style interface

Voice command button

Robot status panel

Example Commands
walk forward
turn left
raise hands
punch
what is the distance
Running the Project
Install dependencies
pip install -r requirements.txt
Start EV3 server
python ev3_humanoid_server.py
Start client GUI
python humanoid_client.py
Project Author

Anish Enduri

Artificial Intelligence & Data Science
Graduating 2026
