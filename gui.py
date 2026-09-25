import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from assistant import process_request, speak


class MacAlexaGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mac Alexa")
        self.root.geometry("760x620")
        self.root.minsize(600, 500)
        self.pending_text = None
        self.busy = False

        header = tk.Frame(self.root, padx=20, pady=16)
        header.pack(fill="x")
        tk.Label(header, text="Mac Alexa", font=("Helvetica", 24, "bold")).pack(anchor="w")
        tk.Label(
            header,
            text="Type a request or use the microphone.",
            font=("Helvetica", 13),
        ).pack(anchor="w", pady=(4, 0))

        self.history = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state="disabled", font=("Helvetica", 13)
        )
        self.history.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        input_frame = tk.Frame(self.root, padx=20, pady=10)
        input_frame.pack(fill="x")

        self.input = tk.Entry(input_frame, font=("Helvetica", 15))
        self.input.pack(side="left", fill="x", expand=True, ipady=7)
        self.input.bind("<Return>", lambda _: self.submit())

        self.send_button = tk.Button(
            input_frame, text="Ask", command=self.submit, width=10, height=2
        )
        self.send_button.pack(side="left", padx=(10, 0))

        voice_frame = tk.Frame(self.root, padx=20, pady=4)
        voice_frame.pack(fill="x")
        self.voice_button = tk.Button(
            voice_frame,
            text="🎙 Start Voice",
            command=self.toggle_voice,
            width=18,
            height=2,
        )
        self.voice_button.pack(side="left")
        tk.Label(
            voice_frame,
            text=" Voice: Hey PC → command",
            font=("Helvetica", 11),
        ).pack(side="left", padx=10)

        self.question_frame = tk.Frame(self.root, padx=20, pady=12)
        tk.Label(
            self.question_frame,
            text="Was this a question?",
            font=("Helvetica", 15, "bold"),
        ).pack(side="left")
        self.yes_button = tk.Button(
            self.question_frame, text="Yes", width=10, height=2,
            command=lambda: self.confirm(True)
        )
        self.yes_button.pack(side="left", padx=(22, 5))
        self.no_button = tk.Button(
            self.question_frame, text="No", width=10, height=2,
            command=lambda: self.confirm(False)
        )
        self.no_button.pack(side="left")

        self.status = tk.Label(
            self.root, text="Ready", anchor="w", padx=20, pady=10
        )
        self.status.pack(fill="x")

        self.voice_recording = False
        self.voice_thread = None
        self.input.focus_set()

    def append(self, text):
        self.history.configure(state="normal")
        self.history.insert(tk.END, text + "\n")
        self.history.see(tk.END)
        self.history.configure(state="disabled")

    def set_input_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.input.configure(state=state)
        self.send_button.configure(state=state)
        if enabled:
            self.input.focus_set()

    def submit(self, text=None):
        if self.busy or self.pending_text:
            return
        text = self.input.get().strip() if text is None else text.strip()
        if not text:
            return
        self.input.delete(0, tk.END)
        self.pending_text = text
        self.append(f"You: {text}")
        self.question_frame.pack(fill="x")
        self.set_input_enabled(False)
        self.status.configure(text="Please choose Yes or No.")

    def confirm(self, is_question):
        if not self.pending_text:
            return
        text = self.pending_text
        self.pending_text = None
        self.question_frame.pack_forget()
        self.busy = True
        self.status.configure(text="Thinking…")

        def worker():
            try:
                answer = process_request(text, is_question=is_question)
                self.root.after(0, lambda: self.answer_ready(answer))
            except Exception as exc:
                self.root.after(0, lambda: self.fail(exc))

        threading.Thread(target=worker, daemon=True).start()

    def answer_ready(self, answer):
        self.append(f"Assistant: {answer}")
        self.status.configure(text="Speaking…")

        def worker():
            try:
                speak(answer)
                self.root.after(0, self.ready)
            except Exception as exc:
                self.root.after(0, lambda: self.fail(exc))

        threading.Thread(target=worker, daemon=True).start()

    def toggle_voice(self):
        if self.voice_recording:
            self.voice_recording = False
            self.voice_button.configure(text="🎙 Start Voice")
            self.status.configure(text="Stopping voice…")
        else:
            self.voice_recording = True
            self.voice_button.configure(text="⏹ Stop Voice")
            self.status.configure(text="Listening for “Hey PC”…")
            self.voice_thread = threading.Thread(target=self.voice_loop, daemon=True)
            self.voice_thread.start()

    def voice_loop(self):
        try:
            from menu_bar import bluetooth_input_device, record_audio, transcribe_audio, WAKE_SECONDS, COMMAND_SECONDS
            from groq import Groq
            import os

            device_index, device_name = bluetooth_input_device()
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

            while self.voice_recording:
                self.root.after(0, lambda n=device_name: self.status.configure(text=f"Listening on {n} — say “Hey PC”"))
                audio = record_audio(device_index, WAKE_SECONDS)
                if not self.voice_recording:
                    break
                wake_text = transcribe_audio(audio, client)

                if "hey pc" not in wake_text.lower():
                    continue

                lower = wake_text.lower()
                start = lower.find("hey pc")
                command = wake_text[start + len("hey pc"):].strip(" ,.!?")

                if not command:
                    self.root.after(0, lambda: self.status.configure(text="Hey PC heard — listening…"))
                    command_audio = record_audio(device_index, COMMAND_SECONDS)
                    command = transcribe_audio(command_audio, client).strip()

                if command:
                    self.voice_recording = False
                    self.root.after(0, lambda t=command: self.voice_captured(t))
                    break

        except Exception as exc:
            self.voice_recording = False
            self.root.after(0, lambda e=exc: self.fail(e))

    def voice_captured(self, text):
        self.voice_button.configure(text="🎙 Start Voice")
        self.submit(text)

    def ready(self):
        self.busy = False
        self.set_input_enabled(True)
        self.status.configure(text="Ready")

    def fail(self, exc):
        self.busy = False
        self.pending_text = None
        self.question_frame.pack_forget()
        self.set_input_enabled(True)
        self.status.configure(text="Error")
        messagebox.showerror("Mac Alexa", str(exc))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    MacAlexaGUI().run()
