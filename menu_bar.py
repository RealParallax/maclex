import os
import tempfile
import threading
import wave
from pathlib import Path

import numpy as np
import rumps
import sounddevice as sd
from groq import Groq

from assistant import ask_ai, bluetooth_context, speak

SAMPLE_RATE = int(os.environ.get("MAC_SAMPLE_RATE", "16000"))
CHANNELS = 1
TRANSCRIPTION_MODEL = os.environ.get("GROQ_TRANSCRIPTION_MODEL", "whisper-large-v3-turbo")


class MacAlexaMenuBar(rumps.App):
    def __init__(self):
        super().__init__("🎙", quit_button=None)
        self.recording = False
        self.frames = []
        self.stream = None
        self.lock = threading.Lock()

        self.listen_item = rumps.MenuItem("Start Listening", callback=self.toggle_recording)
        self.status_item = rumps.MenuItem("Status: Ready")
        self.quit_item = rumps.MenuItem("Quit", callback=self.quit_app)
        self.menu = [self.listen_item, self.status_item, None, self.quit_item]

    def set_status(self, title, icon="🎙"):
        self.title = icon
        self.status_item.title = f"Status: {title}"

    def toggle_recording(self, _):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.recording:
            return
        self.frames = []
        self.recording = True
        self.listen_item.title = "Stop Listening"
        self.set_status("Listening…", "🔴")
        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                callback=self.audio_callback,
            )
            self.stream.start()
        except Exception as exc:
            self.recording = False
            self.stream = None
            self.listen_item.title = "Start Listening"
            self.set_status("Microphone error", "⚠️")
            rumps.alert("Mac Alexa", f"Could not start the microphone:\n\n{exc}")

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Microphone: {status}")
        if self.recording:
            with self.lock:
                self.frames.append(indata.copy())

    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        self.listen_item.title = "Start Listening"

        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        with self.lock:
            frames = list(self.frames)
            self.frames = []

        if not frames:
            self.set_status("Ready", "🎙")
            return

        audio = np.concatenate(frames, axis=0)
        threading.Thread(target=self.process_recording, args=(audio,), daemon=True).start()

    def process_recording(self, audio):
        try:
            self.set_status("Transcribing…", "🟡")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                audio_path = Path(tmp.name)

            try:
                with wave.open(str(audio_path), "wb") as wav:
                    wav.setnchannels(CHANNELS)
                    wav.setsampwidth(2)
                    wav.setframerate(SAMPLE_RATE)
                    wav.writeframes(audio.tobytes())

                client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                with audio_path.open("rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        file=(audio_path.name, audio_file.read()),
                        model=TRANSCRIPTION_MODEL,
                        language="en",
                        response_format="json",
                        temperature=0.0,
                    )

                user_text = transcription.text.strip()
                if not user_text:
                    self.set_status("Ready", "🎙")
                    return

                print(f"You: {user_text}")
                self.set_status("Thinking…", "🟡")
                answer = ask_ai(user_text, bluetooth_context())
                print(f"Assistant: {answer}")

                self.set_status("Speaking…", "🔵")
                speak(answer)
                self.set_status("Ready", "🎙")
            finally:
                audio_path.unlink(missing_ok=True)
        except Exception as exc:
            print(f"Error: {exc}")
            self.set_status("Error", "⚠️")
            rumps.alert("Mac Alexa", f"{exc}")
            self.set_status("Ready", "🎙")

    def quit_app(self, _):
        if self.recording:
            self.stop_recording()
        rumps.quit_application()


if __name__ == "__main__":
    MacAlexaMenuBar().run()
