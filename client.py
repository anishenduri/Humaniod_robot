# ---------------- PART 1 (FINAL, corrected) ----------------
# Core setup, TTS (gTTS+playsound), EV3 socket helper, UI shell (Option B, Neon Blue theme)
# Paste Part-2 then Part-3 AFTER this block, in order, to form the complete program.
# NOTE: This Part-1 defines the UI widgets and the helper functions that Parts 2/3 expect.
# Make sure you have installed:
#   pip install gTTS playsound==1.2.2 fuzzywuzzy speechrecognition google-generativeai
# (If you can't install google.generativeai you can still run the robot controls and local fuzzy matching.)

import socket
import threading
import time
import sys
import tempfile
import os

# TTS imports (gTTS + playsound)
try:
    from gtts import gTTS
except Exception as e:
    print("gTTS import error:", e, file=sys.stderr)
try:
    from playsound import playsound
except Exception as e:
    print("playsound import error:", e, file=sys.stderr)

# GUI imports
import tkinter as tk
from tkinter import ttk, scrolledtext

# ---------------- CONFIG ----------------
SERVER_IP = "169.254.210.40"  # default EV3 IP (change in UI)
SERVER_PORT = 9999
GEMINI_API_KEY = "AIzaSyBNgArvL7wp7DSQVpcnhyN_WKnQzGfmUWc"           # put Gemini key in Part-2 if you use Gemini
GEMINI_MODEL_ID = "gemini-2.5-flash"
FUZZY_THRESHOLD = 70

# ---------------- RELIABLE TTS (gTTS + playsound) ----------------
def speak_text_blocking(text):
    """
    Generate a temporary mp3 with gTTS and play it synchronously using playsound.
    This is called from a background thread via speak_async() to avoid blocking the UI.
    """
    if not text:
        return
    try:
        # Use NamedTemporaryFile with delete=False to avoid issues on Windows
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tf:
            tmp_path = tf.name
        t = gTTS(text=text, lang="en")
        t.save(tmp_path)
        try:
            playsound(tmp_path)
        finally:
            # ensure file removed
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    except Exception as e:
        print("TTS error:", e, file=sys.stderr)

def speak_async(text):
    """Run TTS in a daemon thread so UI stays responsive."""
    try:
        threading.Thread(target=speak_text_blocking, args=(text,), daemon=True).start()
    except Exception as e:
        print("Failed to start TTS thread:", e, file=sys.stderr)

# ---------------- EV3 SOCKET HANDLING ----------------
_client_socket = None
_socket_lock = threading.Lock()

def try_connect_ev3(ip=SERVER_IP, port=SERVER_PORT, timeout=4):
    """
    Attempt to connect to EV3. Returns True on success, False on failure.
    Safe to call multiple times.
    """
    global _client_socket, SERVER_IP, SERVER_PORT
    SERVER_IP, SERVER_PORT = ip, port
    with _socket_lock:
        try:
            if _client_socket:
                try:
                    _client_socket.close()
                except:
                    pass
                _client_socket = None
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((SERVER_IP, SERVER_PORT))
            s.settimeout(None)
            _client_socket = s
            print("Connected to EV3:", SERVER_IP, SERVER_PORT)
            return True
        except Exception as e:
            print("EV3 connect failed:", e, file=sys.stderr)
            _client_socket = None
            return False

def send_command_to_ev3(cmd, wait_for_response=True, recv_buffer=4096, timeout=3):
    """
    Send a command to EV3 and optionally wait for response.
    Returns string response or error message.
    """
    global _client_socket
    with _socket_lock:
        if not _client_socket:
            # try a quick reconnect
            if not try_connect_ev3():
                return "Error: not connected to EV3."
        try:
            _client_socket.sendall(cmd.encode())
            if wait_for_response:
                _client_socket.settimeout(timeout)
                try:
                    data = _client_socket.recv(recv_buffer).decode()
                except socket.timeout:
                    data = "No response (timeout)."
                finally:
                    _client_socket.settimeout(None)
                return data
            return "Command sent."
        except Exception as e:
            print("Socket send error:", e, file=sys.stderr)
            try:
                _client_socket.close()
            except:
                pass
            _client_socket = None
            return f"Error: {e}"

# ---------------- THEME & UI SETUP ----------------
THEME = {
    "bg": "#071320",
    "panel": "#091826",
    "accent": "#05b0ff",
    "muted": "#9fb8c8",
    "btn_bg": "#063a55",
    "btn_fg": "#e9fbff",
    "chat_bg": "#021018",
    "chat_fg": "#dff6ff",
    "card": "#082b36",
}

FONT_HEADING = ("Segoe UI", 14, "bold")
FONT_NORMAL = ("Segoe UI", 11)
FONT_SMALL = ("Segoe UI", 10)

root = tk.Tk()
root.title("🤖 Assistive Robot Client — Neon Blue")
root.geometry("1200x700")
root.configure(bg=THEME["bg"])

# ttk styling
style = ttk.Style(root)
try:
    style.theme_use('clam')
except Exception:
    pass

style.configure("TNotebook", background=THEME["bg"], borderwidth=0)
style.configure("TNotebook.Tab", background=THEME["panel"], foreground=THEME["muted"],
                padding=(12, 8), font=FONT_NORMAL)
style.map("TNotebook.Tab",
          background=[("selected", THEME["bg"])],
          foreground=[("selected", THEME["accent"])])

notebook = ttk.Notebook(root)
notebook.place(relx=0.02, rely=0.03, relwidth=0.96, relheight=0.88)

# ----- Controls tab -----
controls_frame = tk.Frame(notebook, bg=THEME["panel"])
notebook.add(controls_frame, text="Controls")

controls_left = tk.Frame(controls_frame, bg=THEME["panel"])
controls_left.place(relx=0.02, rely=0.03, relwidth=0.62, relheight=0.94)
controls_right = tk.Frame(controls_frame, bg=THEME["panel"])
controls_right.place(relx=0.66, rely=0.03, relwidth=0.32, relheight=0.94)

# Buttons grid (movement + actions)
commands_display = [

    ("Forward", "forward"),
    ("Backward", "backward"),
    ("Stop", "stop"),

    ("Turn Left", "turn_left"),
    ("Turn Right", "turn_right"),
    ("Slide", "slide"),

    ("Auto Mode", "auto"),
    ("Hands Up", "hands_up"),
    ("Hands Down", "hands_down"),

    ("Wave Left", "wave_left"),
    ("Wave Right", "wave_right"),
    ("Punch", "punch"),

    ("Distance", "distance"),
    ("History", "history"),
    ("Exit", "exit"),
]

btn_grid_frame = tk.Frame(controls_left, bg=THEME["panel"])
btn_grid_frame.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.52)

def _make_button(master, text, cmd, row, col):
    b = tk.Button(master, text=text, font=FONT_NORMAL, bd=0, relief=tk.RIDGE,
                  bg=THEME["btn_bg"], fg=THEME["btn_fg"],
                  activebackground=THEME["accent"], activeforeground="#00121a",
                  command=lambda c=cmd: threading.Thread(target=button_send_command, args=(c,), daemon=True).start())
    b.grid(row=row, column=col, padx=8, pady=8, ipadx=8, ipady=10, sticky="nsew")
    return b

rows = 5; cols = 3
for r in range(rows):
    btn_grid_frame.rowconfigure(r, weight=1)
for c in range(cols):
    btn_grid_frame.columnconfigure(c, weight=1)

for idx, (label, cmd) in enumerate(commands_display):
    r = idx // cols
    c = idx % cols
    _make_button(btn_grid_frame, label, cmd, r, c)

# Voice controls (placeholders will be replaced/used by Part-2)
voice_frame = tk.LabelFrame(controls_left, text="Voice Controls", bg=THEME["panel"], fg=THEME["muted"], font=FONT_SMALL)
voice_frame.place(relx=0.02, rely=0.56, relwidth=0.96, relheight=0.28)

btn_manual_voice = tk.Button(voice_frame, text="🎙️ Manual Voice", font=FONT_NORMAL,
                             bg=THEME["btn_bg"], fg=THEME["btn_fg"],
                             command=lambda: threading.Thread(target=manual_voice_capture, daemon=True).start())
btn_manual_voice.place(relx=0.02, rely=0.12, relwidth=0.46, relheight=0.66)

btn_toggle_cont = tk.Button(voice_frame, text="Start Continuous Listening", font=FONT_NORMAL,
                            bg=THEME["btn_bg"], fg=THEME["btn_fg"],
                            command=lambda: toggle_continuous())
btn_toggle_cont.place(relx=0.52, rely=0.12, relwidth=0.46, relheight=0.66)

# Right column status card
status_card = tk.LabelFrame(controls_right, text="Robot Status", bg=THEME["panel"], fg=THEME["muted"], font=FONT_SMALL)
status_card.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.45)

lbl_conn = tk.Label(status_card, text="EV3: disconnected", bg=THEME["card"], fg=THEME["muted"], font=FONT_NORMAL, anchor="w", padx=8)
lbl_conn.place(relx=0.02, rely=0.05, relwidth=0.96, relheight=0.25)

lbl_last_resp = tk.Label(status_card, text="Last response: —", bg=THEME["card"], fg=THEME["muted"], font=FONT_SMALL, anchor="nw", justify="left", padx=8)
lbl_last_resp.place(relx=0.02, rely=0.33, relwidth=0.96, relheight=0.62)

def update_connection_label(connected):
    try:
        if connected:
            lbl_conn.config(text=f"EV3: connected ({SERVER_IP}:{SERVER_PORT})", fg=THEME["accent"])
        else:
            lbl_conn.config(text="EV3: disconnected", fg=THEME["muted"])
    except Exception:
        pass

def set_last_response(text):
    try:
        lbl_last_resp.config(text=f"Last response:\n{text}")
    except Exception:
        pass

# Quick connect controls
connect_frame = tk.Frame(controls_right, bg=THEME["panel"])
connect_frame.place(relx=0.02, rely=0.50, relwidth=0.96, relheight=0.30)

entry_ip = tk.Entry(connect_frame, font=FONT_SMALL)
entry_ip.insert(0, SERVER_IP)
entry_ip.place(relx=0.02, rely=0.12, relwidth=0.6, relheight=0.32)

entry_port = tk.Entry(connect_frame, font=FONT_SMALL)
entry_port.insert(0, str(SERVER_PORT))
entry_port.place(relx=0.02, rely=0.52, relwidth=0.28, relheight=0.32)

def on_quick_connect():
    ip = entry_ip.get().strip()
    try:
        port = int(entry_port.get().strip())
    except:
        port = SERVER_PORT
    connected = try_connect_ev3(ip=ip, port=port)
    update_connection_label(connected)
    set_last_response("Connected." if connected else "Failed to connect.")

btn_quick_connect = tk.Button(connect_frame, text="Connect", font=FONT_NORMAL, command=on_quick_connect,
                              bg=THEME["accent"], fg="#00121a")
btn_quick_connect.place(relx=0.66, rely=0.22, relwidth=0.32, relheight=0.56)

# ----- Chat Tab -----
chat_frame = tk.Frame(notebook, bg=THEME["chat_bg"])
notebook.add(chat_frame, text="Chat")

# -------- WhatsApp-style Chat Area --------
chat_canvas = tk.Canvas(chat_frame, bg=THEME["chat_bg"], highlightthickness=0)
chat_canvas.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.78)

chat_scrollbar = tk.Scrollbar(chat_frame, command=chat_canvas.yview)
chat_scrollbar.place(relx=0.98, rely=0.02, relheight=0.78)

chat_canvas.configure(yscrollcommand=chat_scrollbar.set)

chat_inner = tk.Frame(chat_canvas, bg=THEME["chat_bg"])
chat_window = chat_canvas.create_window((0, 0), window=chat_inner, anchor="nw")

def _on_chat_configure(event):
    chat_canvas.configure(scrollregion=chat_canvas.bbox("all"))

chat_inner.bind("<Configure>", _on_chat_configure)

input_frame = tk.Frame(chat_frame, bg=THEME["chat_bg"])
input_frame.place(relx=0.02, rely=0.82, relwidth=0.96, relheight=0.15)

txt_entry = tk.Entry(input_frame, font=FONT_NORMAL)
txt_entry.place(relx=0.01, rely=0.12, relwidth=0.78, relheight=0.75)

def on_send_text(event=None):
    text = txt_entry.get().strip()
    if not text:
        return
    txt_entry.delete(0, tk.END)
    # process_input_text is defined in Part-2; call it in a background thread to be safe
    try:
        threading.Thread(target=process_input_text, args=(text, "typed"), daemon=True).start()
    except Exception:
        # if Part-2 not yet pasted, fallback
        append_chat_message("You", text)
        append_chat_message("System", "process_input_text not available (paste Part-2).")

txt_entry.bind("<Return>", on_send_text)

send_btn = tk.Button(input_frame, text="Send", bg=THEME["accent"], fg="#00121a", command=on_send_text)
send_btn.place(relx=0.81, rely=0.12, relwidth=0.18, relheight=0.75)

# Footer / status
status_label = tk.Label(root, text="Developed by ANISH", fg=THEME["muted"], bg=THEME["bg"], font=FONT_SMALL)
status_label.place(relx=0.02, rely=0.93, relwidth=0.96, relheight=0.04)

# ----- Button handler uses send_command_to_ev3 & append_chat_message (safe now) -----
def button_send_command(cmd):
    """Send a command when control-buttons are pressed (runs in background thread)."""
    append_chat_message("You", f"[BUTTON] {cmd}")
    append_chat_message("System", f"Sending: {cmd}")
    def _send():
        resp = send_command_to_ev3(cmd)
        append_chat_message("Robot", resp)
        set_last_response(resp)
        # speak using speak_async (reliable)
        speak_async(resp)
    threading.Thread(target=_send, daemon=True).start()

# placeholders — actual implementations are supplied in Part-2
def manual_voice_capture():
    append_chat_message("System", "Voice capture not ready — paste Part-2 & Part-3.")
    return

cont_listening = {"running": False, "thread": None}
def toggle_continuous():
    append_chat_message("System", "Continuous listening not ready — paste Part-2 & Part-3.")
    return

# Thread-safe append (Parts 2 overrides it with richer version, but define here so UI works standalone)
def append_chat_message(sender, message):
    def _append():
        is_user = sender.lower().startswith("you")
        
        bubble_bg = "#05b0ff" if is_user else "#1e2a32"
        bubble_fg = "#ffffff"
        align = "e" if is_user else "w"
        pad_x = (80, 10) if is_user else (10, 80)

        container = tk.Frame(chat_inner, bg=THEME["chat_bg"])
        container.pack(fill="x", pady=4)

        bubble = tk.Label(
            container,
            text=message,
            bg=bubble_bg,
            fg=bubble_fg,
            font=("Segoe UI", 11),
            wraplength=420,
            justify="left",
            padx=10,
            pady=6
        )

        bubble.pack(anchor=align, padx=pad_x)

        chat_canvas.update_idletasks()
        chat_canvas.yview_moveto(1.0)

    root.after(0, _append)


# Graceful exit (Part-3 will finalize close_app; define safe minimal)
def close_app():
    try:
        cont_listening["running"] = False
    except:
        pass
    try:
        if _client_socket:
            _client_socket.close()
    except:
        pass
    try:
        root.destroy()
    except:
        os._exit(0)

root.protocol("WM_DELETE_WINDOW", close_app)

# Do NOT call root.mainloop() here. Part-3 will call mainloop after all parts are pasted.
append_chat_message("System", "PART-1 loaded. Now paste Part-2 and Part-3, then run the combined file.")
# ---------------- END PART 1 ----------------

# ---------------- PART 2/3 ----------------
# Voice system, fuzzy matching, Gemini intent extraction, and core processing.
# Paste this AFTER Part 1 and BEFORE Part 3.

# Extra imports (safe if already imported)
try:
    import speech_recognition as sr
except Exception as e:
    print("speech_recognition import error:", e)

try:
    from fuzzywuzzy import process as fw_process
except Exception as e:
    print("fuzzywuzzy import error:", e)

# Gemini availability check
HAS_GEMINI = False
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        HAS_GEMINI = True
    else:
        print("Gemini API Key not found — Gemini disabled.")
except Exception as e:
    print("Gemini import error:", e)

# ---------------- COMMANDS ----------------
COMMAND_PHRASES = {

    # MOVEMENT
    "forward": "forward",
    "move forward": "forward",
    "go forward": "forward",
    "walk forward": "forward",

    "backward": "backward",
    "move backward": "backward",
    "go back": "backward",
    "reverse": "backward",

    "stop": "stop",
    "halt": "stop",

    # TURN
    "turn left": "turn_left",
    "rotate left": "turn_left",
    "left": "turn_left",

    "turn right": "turn_right",
    "rotate right": "turn_right",
    "right": "turn_right",

    # SLIDE
    "slide": "slide",
    "slide move": "slide",

    # AUTO MODE
    "auto": "auto",
    "autonomous": "auto",
    "automatic mode": "auto",
    "avoid obstacle": "auto",

    # HAND MOVEMENTS
    "hands up": "hands_up",
    "raise hands": "hands_up",
    "lift hands": "hands_up",

    "hands down": "hands_down",
    "lower hands": "hands_down",

    # WAVES
    "wave left": "wave_left",
    "left wave": "wave_left",

    "wave right": "wave_right",
    "right wave": "wave_right",

    # ACTION
    "punch": "punch",
    "hit": "punch",

    # SENSOR
    "distance": "distance",
    "how far": "distance",
    "measure distance": "distance",

    # HISTORY
    "history": "history",
    "command history": "history",

    # EXIT
    "exit": "exit",
    "shutdown": "exit",
    "disconnect": "exit",
}


COMMAND_KEYS = list(COMMAND_PHRASES.keys())
COMMAND_VALUES = set(COMMAND_PHRASES.values())

# ---------------- GEMINI HELPERS ----------------

def _instantiate_gemini_model():
    if not HAS_GEMINI:
        return None
    try:
        if hasattr(genai, "GenerativeModel"):
            return genai.GenerativeModel(GEMINI_MODEL_ID)
        if hasattr(genai, "get_model"):
            return genai.get_model(GEMINI_MODEL_ID)
        return None
    except Exception as e:
        print("Gemini model load error:", e)
        return None

_GEMINI_MODEL = _instantiate_gemini_model()

def gemini_extract_intent(text):
    """Extract robot-intent using Gemini. Returns command or None."""
    if not _GEMINI_MODEL:
        return None

    prompt = f"""
You are an intent-extractor for a robot.

User message:
{text}

Return exactly ONE command from:
{', '.join(sorted(COMMAND_VALUES))}

If none apply, return: none
"""

    try:
        if hasattr(_GEMINI_MODEL, "generate_content"):
            resp = _GEMINI_MODEL.generate_content(prompt)
            extracted = resp.text.strip().lower()
        else:
            resp = genai.generate(model=GEMINI_MODEL_ID, prompt=prompt)
            extracted = str(resp).strip().lower()

        token = extracted.split()[0]
        return token if token in COMMAND_VALUES else None

    except Exception as e:
        print("Gemini intent error:", e)
        return None


def ask_gemini_chat(text):
    """General chat with Gemini (1-2 short sentences, clean for TTS)."""
    if not _GEMINI_MODEL:
        return "Gemini is not configured."

    prompt = f"""
You are a helpful assistant. Reply to the user's query in 1-2 short sentences only.
User: "{text}"
"""
    try:
        if hasattr(_GEMINI_MODEL, "generate_content"):
            resp = _GEMINI_MODEL.generate_content(prompt)
            reply = resp.text.strip()
        else:
            resp = genai.generate(model=GEMINI_MODEL_ID, prompt=prompt)
            reply = str(resp).strip()
        
        # Clean reply: remove leading/trailing asterisks and extra whitespace
        reply_clean = reply.strip("*").strip()
        return reply_clean

    except Exception as e:
        print("Gemini chat error:", e)
        return "Error reaching Gemini."



# ---------------- FUZZY MATCH ----------------

def fuzzy_map_to_command(text):
    """Local fuzzy fallback when Gemini doesn't understand."""
    if not text:
        return None

    try:
        match = fw_process.extractOne(text.lower(), COMMAND_KEYS)
        if match:
            phrase, score = match
            if score >= FUZZY_THRESHOLD:
                return COMMAND_PHRASES[phrase]
    except Exception as e:
        print("Fuzzy error:", e)

    return None


# ---------------- CORE PROCESSING ----------------

def process_input_text(user_text, source="typed"):
    """Handles typed/voice input → command or chat."""
    if not user_text:
        return

    user_text = user_text.strip()
    append_chat_message("You" if source == "typed" else "You (voice)", user_text)

    # 1) Fuzzy
    cmd = fuzzy_map_to_command(user_text)

    # 2) Gemini intent
    if not cmd:
        cmd = gemini_extract_intent(user_text)

    # If command found → send to robot
    if cmd:
        append_chat_message("System", f"Command detected: {cmd}")

        def _robot_send():
            resp = send_command_to_ev3(cmd)
            append_chat_message("Robot", resp)
            set_last_response(resp)
            update_connection_label("Error" not in resp)
            speak_async(resp)

        threading.Thread(target=_robot_send, daemon=True).start()
        return

    # Else → normal chat with Gemini
    def _chat():
        reply = ask_gemini_chat(user_text)
        # clean reply: strip whitespace & asterisks
        reply_clean = reply.strip().strip("*")
        append_chat_message("Robo", reply_clean)
        speak_async(reply_clean)

    threading.Thread(target=_chat, daemon=True).start()


# ---------------- SPEECH RECOGNITION ----------------

recognizer = sr.Recognizer() if 'sr' in globals() else None

def manual_voice_capture():
    """Runs when user presses mic button."""
    if not recognizer:
        append_chat_message("System", "Speech recognition unavailable.")
        return

    append_chat_message("System", "Listening...")

    try:
        with sr.Microphone() as mic:
            recognizer.adjust_for_ambient_noise(mic, duration=0.4)
            audio = recognizer.listen(mic, timeout=6, phrase_time_limit=6)
            text = recognizer.recognize_google(audio).lower()
            append_chat_message("You (voice)", text)

            cleaned = text.replace("robo", "").strip()
            process_input_text(cleaned, source="voice")

    except sr.WaitTimeoutError:
        append_chat_message("System", "Timed out.")
    except sr.UnknownValueError:
        append_chat_message("System", "Didn't catch that.")
    except Exception as e:
        append_chat_message("System", f"Voice Err: {e}")


# ---------------- CONTINUOUS LISTENING ----------------

def continuous_listen_loop():
    if not recognizer:
        append_chat_message("System", "Speech recognition unavailable.")
        cont_listening["running"] = False
        return

    with sr.Microphone() as mic:
        recognizer.adjust_for_ambient_noise(mic, duration=0.5)
        append_chat_message("System", "Continuous listening ON.")

        while cont_listening["running"]:
            try:
                audio = recognizer.listen(mic, timeout=6, phrase_time_limit=5)
                text = recognizer.recognize_google(audio).lower()
                append_chat_message("You (voice)", text)

                cleaned = text.replace("robo", "").strip()
                process_input_text(cleaned, source="voice")

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                append_chat_message("System", "Didn't understand (cont).")
            except Exception as e:
                append_chat_message("System", f"Cont error: {e}")
                time.sleep(0.5)

        append_chat_message("System", "Continuous listening OFF.")

def toggle_continuous():
    if not cont_listening["running"]:
        cont_listening["running"] = True
        cont_listening["thread"] = threading.Thread(target=continuous_listen_loop, daemon=True)
        cont_listening["thread"].start()
        btn_toggle_cont.config(text="Stop Continuous Listening", bg="#b22222")
    else:
        cont_listening["running"] = False
        btn_toggle_cont.config(text="Start Continuous Listening", bg=THEME["btn_bg"])
        append_chat_message("System", "Stopping...")


# ---------------- CHAT HISTORY ----------------

MESSAGE_HISTORY = []

def append_chat_message(sender, message):
    def _append():
        is_user = sender.lower().startswith("you")
        
        bubble_bg = "#05b0ff" if is_user else "#1e2a32"
        bubble_fg = "#ffffff"
        align = "e" if is_user else "w"
        pad_x = (80, 10) if is_user else (10, 80)

        container = tk.Frame(chat_inner, bg=THEME["chat_bg"])
        container.pack(fill="x", pady=4)

        bubble = tk.Label(
            container,
            text=message,
            bg=bubble_bg,
            fg=bubble_fg,
            font=("Segoe UI", 11),
            wraplength=420,
            justify="left",
            padx=10,
            pady=6
        )

        bubble.pack(anchor=align, padx=pad_x)

        chat_canvas.update_idletasks()
        chat_canvas.yview_moveto(1.0)

    root.after(0, _append)



# ---------------- AUTO CONNECT ----------------

def _initial_connect():
    ok = try_connect_ev3()
    root.after(0, lambda: update_connection_label(ok))
    if ok:
        set_last_response("Connected.")

threading.Thread(target=_initial_connect, daemon=True).start()

# ---------------- END PART 2/3 ----------------
# ---------------- PART 3/3 ----------------
# Final integration, UI polish, helpers, and mainloop.
# Paste this AFTER Part 2. Then run the single concatenated file.

import json
import os
from datetime import datetime

# ---------------- SMALL UI POLISHING / EXTRA CONTROLS ----------------

#
util_frame = tk.Frame(chat_frame, bg=THEME["chat_bg"])
util_frame.place(relx=0.02, rely=0.96, relwidth=0.96, relheight=0.03)

def clear_chat():
    chat_display.configure(state=tk.NORMAL)
    chat_display.delete("1.0", tk.END)
    chat_display.configure(state=tk.DISABLED)
    append_chat_message("System", "Chat cleared.")

def export_history():
    if not MESSAGE_HISTORY:
        append_chat_message("System", "No messages to export.")
        return
    fname = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        data = [{"ts": t, "sender": s, "message": m} for (t, s, m) in MESSAGE_HISTORY]
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        append_chat_message("System", f"History exported to {os.path.abspath(fname)}")
    except Exception as e:
        append_chat_message("System", f"Export failed: {e}")

btn_clear = tk.Button(util_frame, text="Clear Chat", font=("Segoe UI", 9), command=clear_chat,
                      bg=THEME["btn_bg"], fg=THEME["btn_fg"])
btn_clear.place(relx=0.0, rely=0.0, relwidth=0.12, relheight=1.0)

btn_export = tk.Button(util_frame, text="Export History", font=("Segoe UI", 9), command=export_history,
                       bg=THEME["btn_bg"], fg=THEME["btn_fg"])
btn_export.place(relx=0.13, rely=0.0, relwidth=0.16, relheight=1.0)

# Help button
def show_help():
    help_text = (
        "Controls:\n"
        "- Use Buttons to send direct EV3 commands.\n"
        "- Manual Voice: captures single utterance.\n"
        "- Continuous Listening: listens until toggled off.\n"
        "- Type in Chat tab to send text to Gemini or map to robot commands.\n\n"
        "Notes:\n- Ensure EV3 IP/port are correct and reachable.\n- If Gemini not configured, chat will fall back to a message.\n- TTS handled by single background thread to avoid pyttsx3 locking."
    )
    append_chat_message("Help", help_text)

btn_help = tk.Button(util_frame, text="Help", font=("Segoe UI", 9), command=show_help,
                     bg=THEME["btn_bg"], fg=THEME["btn_fg"])
btn_help.place(relx=0.30, rely=0.0, relwidth=0.12, relheight=1.0)

# ---------------- BINDINGS & SMALL UX ----------------

# Allow clicking Enter to send in chat (already bound), but also provide Escape to clear entry
def on_escape(event=None):
    txt_entry.delete(0, tk.END)

root.bind("<Escape>", on_escape)

# Update labels periodically (health check)
def _health_check():
    # update connection label color based on socket state
    connected = _client_socket is not None
    update_connection_label(connected)
    # schedule next check
    root.after(3000, _health_check)

root.after(3000, _health_check)

# ---------------- FINALIZE CLEANUP ----------------
def close_app():
    # stop continuous listening
    try:
        cont_listening["running"] = False
    except Exception:
        pass

    # stop TTS thread by sending sentinel
    try:
        _tts_queue.put_nowait(None)
    except Exception:
        pass

    # close socket
    try:
        if _client_socket:
            _client_socket.close()
    except Exception:
        pass

    # small delay to let threads finish (non-blocking short sleep)
    time.sleep(0.15)
    try:
        root.destroy()
    except Exception:
        os._exit(0)

root.protocol("WM_DELETE_WINDOW", close_app)

# ---------------- START MAINLOOP ----------------
append_chat_message("System", "Ready. Use Controls tab or Chat tab. Say 'Anish' optionally.")
update_connection_label(_client_socket is not None)
root.mainloop()

# ---------------- END PART 3/3 ----------------
