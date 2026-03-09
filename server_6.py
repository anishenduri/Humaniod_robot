#!/usr/bin/env python3

import socket
import time
import threading
from ev3dev2.motor import LargeMotor, OUTPUT_B, OUTPUT_C, OUTPUT_A, OUTPUT_D, SpeedPercent
from ev3dev2.sensor.lego import UltrasonicSensor

HOST = ''
PORT = 9999

# ----------------- MOTORS -----------------
left_leg = LargeMotor(OUTPUT_B)
right_leg = LargeMotor(OUTPUT_C)
left_hand = LargeMotor(OUTPUT_A)
right_hand = LargeMotor(OUTPUT_D)

# ----------------- SENSOR -----------------
ultra_sensor = UltrasonicSensor('in3')

# ----------------- CONTROL -----------------
movement_thread = None
movement_running = False
command_history = []

OBSTACLE_THRESHOLD = 40
SPEED = 90


# ----------------- BASIC MOVEMENTS (UNCHANGED) -----------------

def walk_forward():
    global movement_running
    movement_running = True

    while movement_running:
        if ultra_sensor.distance_centimeters < OBSTACLE_THRESHOLD:
            left_leg.off()
            right_leg.off()
            movement_running = False
            command_history.append("Obstacle detected")
            return

        left_leg.on_for_degrees(SpeedPercent(SPEED), 180, block=True)
        right_leg.on_for_degrees(SpeedPercent(SPEED), 180, block=True)
        time.sleep(0.1)

    left_leg.off()
    right_leg.off()


def walk_backward():
    global movement_running
    movement_running = True

    while movement_running:
        left_leg.on_for_degrees(SpeedPercent(-SPEED), 180, block=True)
        right_leg.on_for_degrees(SpeedPercent(-SPEED), 180, block=True)
        time.sleep(0.1)

    left_leg.off()
    right_leg.off()


def turn_left():
    left_leg.on_for_degrees(SpeedPercent(-SPEED), 180, block=True)
    right_leg.on_for_degrees(SpeedPercent(SPEED), 180, block=True)


def turn_right():
    left_leg.on_for_degrees(SpeedPercent(SPEED), 180, block=True)
    right_leg.on_for_degrees(SpeedPercent(-SPEED), 180, block=True)


def slide():
    global movement_running
    movement_running = True

    left_leg.on(SpeedPercent(SPEED))
    right_leg.on(SpeedPercent(SPEED))

    while movement_running:
        time.sleep(0.1)

    left_leg.off()
    right_leg.off()


def obstacle_avoidance():
    global movement_running
    movement_running = True

    while movement_running:
        dist = ultra_sensor.distance_centimeters

        if dist < OBSTACLE_THRESHOLD:
            left_leg.on_for_degrees(SpeedPercent(-SPEED), 180, block=True)
            right_leg.on_for_degrees(SpeedPercent(-SPEED), 180, block=True)

            left_leg.on_for_degrees(SpeedPercent(-SPEED), 180, block=True)
            right_leg.on_for_degrees(SpeedPercent(SPEED), 180, block=True)
        else:
            left_leg.on_for_degrees(SpeedPercent(SPEED), 180, block=True)
            right_leg.on_for_degrees(SpeedPercent(SPEED), 180, block=True)

        time.sleep(0.1)

    left_leg.off()
    right_leg.off()


# ----------------- HAND SYNC FIX -----------------

def move_hands_together(speed, degrees):
    left_hand.on_for_degrees(SpeedPercent(speed), degrees, block=False)
    right_hand.on_for_degrees(SpeedPercent(speed), degrees, block=False)

    while left_hand.is_running or right_hand.is_running:
        time.sleep(0.01)


def punch():
    right_hand.on_for_degrees(SpeedPercent(-80), 120, block=True)
    right_hand.on_for_degrees(SpeedPercent(80), 120, block=True)


# ----------------- EXECUTE COMMAND -----------------

def execute_command(cmd):
    global movement_thread, movement_running, SPEED
    cmd = cmd.strip().lower()

    if cmd == "forward":
        if movement_thread and movement_thread.is_alive():
            return "Already moving"
        movement_thread = threading.Thread(target=walk_forward)
        movement_thread.start()
        return "Walking forward"

    elif cmd == "backward":
        if movement_thread and movement_thread.is_alive():
            return "Already moving"
        movement_thread = threading.Thread(target=walk_backward)
        movement_thread.start()
        return "Walking backward"

    elif cmd == "stop":
        movement_running = False
        return "Stopped"

    elif cmd == "turn_left":
        turn_left()
        return "Turned left"

    elif cmd == "turn_right":
        turn_right()
        return "Turned right"

    elif cmd == "slide":
        if movement_thread and movement_thread.is_alive():
            return "Already moving"
        movement_thread = threading.Thread(target=slide)
        movement_thread.start()
        return "Sliding"

    elif cmd == "auto":
        if movement_thread and movement_thread.is_alive():
            return "Already moving"
        movement_thread = threading.Thread(target=obstacle_avoidance)
        movement_thread.start()
        return "Autonomous mode activated"

    elif cmd == "hands_up":
        move_hands_together(-50, 90)
        return "Hands raised together"

    elif cmd == "hands_down":
        move_hands_together(50, 90)
        return "Hands lowered together"

    elif cmd == "wave_left":
        left_hand.on_for_degrees(SpeedPercent(-60), 90, block=True)
        left_hand.on_for_degrees(SpeedPercent(60), 90, block=True)
        return "Waved left hand"

    elif cmd == "wave_right":
        right_hand.on_for_degrees(SpeedPercent(-60), 90, block=True)
        right_hand.on_for_degrees(SpeedPercent(60), 90, block=True)
        return "Waved right hand"

    elif cmd == "punch":
        punch()
        return "Punch executed"

    elif cmd == "distance":
        dist = ultra_sensor.distance_centimeters
        return "Distance is " + str(int(dist)) + " centimeters"

    elif cmd.startswith("speed"):
        parts = cmd.split()
        if len(parts) == 2:
            try:
                new_speed = int(parts[1])
                if new_speed >= 10 and new_speed <= 100:
                    SPEED = new_speed
                    return "Speed set to " + str(SPEED)
            except:
                return "Invalid speed value"
        return "Invalid speed command"

    elif cmd == "history":
        if command_history:
            return "\n".join(command_history)
        else:
            return "No commands yet"

    elif cmd == "exit":
        movement_running = False
        return "exit"

    return "Unknown command"


# ----------------- TCP SERVER -----------------

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    print("Humanoid EV3 Server running...")

    conn, addr = s.accept()
    with conn:
        print("Connected by", addr)
        while True:
            data = conn.recv(1024)

            if not data:
                left_leg.off()
                right_leg.off()
                left_hand.off()
                right_hand.off()
                break

            command = data.decode().strip()
            command_history.append(command)

            response = execute_command(command)

            if response:
                conn.sendall(response.encode())

            if response == "exit":
                left_leg.off()
                right_leg.off()
                left_hand.off()
                right_hand.off()
                break