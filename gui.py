import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from assistant import process_request, speak


class MacAlexaGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mac Alexa")
        self.root.geometry("620x520")
        self.root.minsize(500, 420)
        self.pending_text = None
        self.busy = False

        header = tk.Frame(self.root, padx=18, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="Mac Alexa", font=("Helvetica", 22, "bold")).pack(anchor="w")
        tk.Label(header, text="Type a request below.", font=("Helvetica", 12)).pack(anchor="w", pady=(4, 0))

        self.history = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state="disabled", font=("Helvetica", 13)
        )
        self.history.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        input_frame = tk.Frame(self.root, padx=18, pady=10)
        input_frame.pack(fill="x")
        self.input = tk.Entry(input_frame, font=("Helvetica", 14))
        self.input.pack(side="left", fill="x", expand=True)
        self.input.bind("<Return>", lambda _: self.submit())
        self.send_button = tk.Button(input_frame, text="Ask", command=self.submit, width=10)
        self.send_button.pack(side="left", padx=(8, 0))

        self.question_frame = tk.Frame(self.root, padx=18, pady=10)
        tk.Label(self.question_frame, text="Was this a question?", font=("Helvetica", 14, "bold")).pack(side="left")
        tk.Button(self.question_frame, text="Yes", width=8, command=lambda: self.confirm(True)).pack(side="left", padx=(18, 4))
        tk.Button(self.question_frame, text="No", width=8, command=lambda: self.confirm(False)).pack(side="left")

        self.status = tk.Label(self.root, text="Ready", anchor="w", padx=18, pady=8)
        self.status.pack(fill="x")
        self.input.focus_set()

    def append(self, text):
        self.history.configure(state="normal")
        self.history.insert(tk.END, text + "\n")
        self.history.see(tk.END)
        self.history.configure(state="disabled")

    def submit(self):
        if self.busy:
            return
        text = self.input.get().strip()
        if not text:
            return
        self.input.delete(0, tk.END)
        self.pending_text = text
        self.append(f"You: {text}")
        self.question_frame.pack(fill="x")
        self.input.configure(state="disabled")
        self.send_button.configure(state="disabled")
        self.status.configure(text="Please choose Yes or No.")

    def confirm(self, is_question):
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

    def ready(self):
        self.busy = False
        self.input.configure(state="normal")
        self.send_button.configure(state="normal")
        self.input.focus_set()
        self.status.configure(text="Ready")

    def fail(self, exc):
        self.busy = False
        self.input.configure(state="normal")
        self.send_button.configure(state="normal")
        self.input.focus_set()
        self.status.configure(text="Error")
        messagebox.showerror("Mac Alexa", str(exc))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    MacAlexaGUI().run()
