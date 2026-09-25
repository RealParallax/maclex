import os
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np
import rumps
import sounddevice as sd
from groq import Groq

from assistant import ask_ai, bluetooth_context, speak

SAMPLE_RATE = int(os.environ.get("MAC_SAMPLE_RATE", "16000"))
CHANNELS = 1
WAKE_SECONDS = float(os.environ.get("MAC_WAKE_SECONDS", "2.5"))
COMMAND_SECONDS = float(os.environ.get("MAC_COMMAND_SECONDS", "10"))
TRANSCRIPTION_MODEL = os.environ.get("GROQ_TRANSCRIPTION_MODEL", "whisper-large-v3-turbo")
WAKE_PHRASE = os.environ.get("MAC_WAKE_PHRASE", "hey pc").lower()


def bluetooth_input_device():
    requested = os.environ.get("MAC_MIC_DEVICE", "").strip().lower()
    devices = sd.query_devices()

    if requested:
        for index, device in enumerate(devices):
            if device["max_input_channels"] > 0 and requested in device["name"].lower():
                return index, device["name"]
        raise RuntimeError(
            f'MAC_MIC_DEVICE="{os.environ["MAC_MIC_DEVICE"]}" was not found. '
            "Run sounddevice device listing to see available microphones."
        )

    excluded = (
        "built-in microphone",
        "built-in mic",
        "macbook microphone",
        "macbook pro microphone",
        "macbook air microphone",
        "internal microphone",
    )
    candidates = []
    for index, device in enumerate(devices):
        name = device["name"].lower()
        if device["max_input_channels"] <= 0 or any(x in name for x in excluded):
            continue
        score = 0
        if any(x in name for x in ("airpods", "beats", "bluetooth", "buds", "headset", "headphones")):
            score += 100
        if "microphone" in name or "mic" in name:
            score += 10
        candidates.append((score, index, device["name"]))

    if not candidates:
        raise RuntimeError(
            "No external microphone was found. Connect your Bluetooth headset/microphone "
            "or set MAC_MIC_DEVICE to its device name."
        )

    candidates.sort(reverse=True)
    _, index, name = candidates[0]
    return index, name


def record_audio(device_index, seconds):
    frames = []

    def callback(indata, frames_count, time_info, status):
        if status:
            print(f"Microphone: {status}")
        frames.append(indata.copy())

    with sd.InputStream(
        device=device_index,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        callback=callback,
    ):
        time.sleep(seconds)

    if not frames:
        return np.empty((0, CHANNELS), dtype=np.int16)
    return np.concatenate(frames, axis=0)


def transcribe_audio(audio, client):
    if len(audio) == 0:
        return ""

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = Path(tmp.name)

    try:
        with wave.open(str(audio_path), "wb") as wav:
            wav.setnchannels(CHANNELS)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(audio.tobytes())

        with audio_path.open("rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(audio_path.name, audio_file.read()),
                model=TRANSCRIPTION_MODEL,
                language="en",
                response_format="json",
                temperature=0.0,
            )
        return transcription.text.strip()
    finally:
        audio_path.unlink(missing_ok=True)


def contains_wake_phrase(text):
    normalized = " ".join(text.lower().split())
    return WAKE_PHRASE in normalized


class MacAlexaMenuBar(rumps.App):
    def __init__(self):
        super().__init__("🎙", quit_button=None)
        self.running = True
        self.processing = False
        self.listen_item = rumps.MenuItem("Listening for “Hey PC”…", callback=self.toggle_listening)
        self.status_item = rumps.MenuItem("Status: Starting…")
        self.quit_item = rumps.MenuItem("Quit", callback=self.quit_app)
        self.menu = [self.listen_item, self.status_item, None, self.quit_item]
        self.thread = threading.Thread(target=self.wake_loop, daemon=True)
        self.thread.start()

    def set_status(self, title, icon="🎙"):
        self.title = icon
        self.status_item.title = f"Status: {title}"

    def toggle_listening(self, _):
        self.running = not self.running
        if self.running:
            self.listen_item.title = "Listening for “Hey PC”…"
            self.set_status("Waiting for Hey PC", "🎙")
            if not self.thread.is_alive():
                self.thread = threading.Thread(target=self.wake_loop, daemon=True)
                self.thread.start()
        else:
            self.listen_item.title = "Start Listening for “Hey PC”"
            self.set_status("Paused", "⏸️")

    def wake_loop(self):
        try:
            device_index, device_name = bluetooth_input_device()
            print(f"Using microphone: {device_name}")
            self.set_status(f"Mic: {device_name}", "🎙")
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

            while self.running:
                if self.processing:
                    time.sleep(0.1)
                    continue

                audio = record_audio(device_index, WAKE_SECONDS)
                text = transcribe_audio(audio, client)
                if not text:
                    continue

                print(f"Wake check: {text}")
                if contains_wake_phrase(text):
                    self.processing = True
                    threading.Thread(
                        target=self.handle_wake,
                        args=(device_index, client),
                        daemon=True,
                    ).start()

        except Exception as exc:
            print(f"Wake loop error: {exc}")
            self.set_status("Microphone error", "⚠️")
            rumps.alert("Mac Alexa", str(exc))
            self.running = False
            self.listen_item.title = "Start Listening for “Hey PC”"

    def handle_wake(self, device_index, client):
        try:
            self.set_status("Listening for command…", "🔴")
            audio = record_audio(device_index, COMMAND_SECONDS)
            user_text = transcribe_audio(audio, client)

            normalized = user_text.strip()
            if contains_wake_phrase(normalized):
                lower = normalized.lower()
                start = lower.find(WAKE_PHRASE)
                normalized = normalized[start + len(WAKE_PHRASE):].strip(" ,.!?")

            if not normalized:
                self.set_status("Waiting for Hey PC", "🎙")
                return

            print(f"You: {normalized}")
            self.set_status("Thinking…", "🟡")
            answer = ask_ai(normalized, bluetooth_context())
            print(f"Assistant: {answer}")

            self.set_status("Speaking…", "🔵")
            speak(answer)
            self.set_status("Waiting for Hey PC", "🎙")
        except Exception as exc:
            print(f"Error: {exc}")
            self.set_status("Error", "⚠️")
            rumps.alert("Mac Alexa", str(exc))
            self.set_status("Waiting for Hey PC", "🎙")
        finally:
            self.processing = False

    def quit_app(self, _):
        self.running = False
        rumps.quit_application()


if __name__ == "__main__":
    MacAlexaMenuBar().run()
