import os
import re
import subprocess

from groq import Groq
from bluetooth_devices import scan_bluetooth

SYSTEM_PROMPT = """You are a polished, friendly voice assistant running locally on a Mac.
Sound like a modern smart speaker assistant: calm, warm, confident, and natural.
Keep answers concise and conversational because they will be spoken aloud.
Do not use markdown, bullet points, emojis, or unnecessary filler in spoken answers.
You can answer general questions. If the user asks about Bluetooth devices,
use the device information supplied by the application.
Do not claim to have performed an action unless the application actually did it.
"""

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
VOICE = os.environ.get("MAC_VOICE", "Samantha")
VOICE_RATE = os.environ.get("MAC_VOICE_RATE", "175")


_bluetooth_info = None


def bluetooth_context(force_refresh=False) -> str:
    global _bluetooth_info
    if _bluetooth_info is None or force_refresh:
        devices = scan_bluetooth()
    _bluetooth_info = "\n".join(
        f"- {d['name'] or '(unnamed)'} [{d['address']}] RSSI={d['rssi']}"
        for d in devices
    ) or "No BLE devices were discovered."
    return _bluetooth_info


def ask_ai(user_text: str, bluetooth_info: str | None = None, is_question: bool = True) -> str:
    if bluetooth_info is None:
        bluetooth_info = bluetooth_context()
    request_kind = "question" if is_question else "command or statement"
    prompt = f"""Bluetooth information from this Mac:

{bluetooth_info}

The user classified this as a {request_kind}.

User request:
{user_text}
"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=180,
    )
    return response.choices[0].message.content.strip()


def speak(text: str):
    spoken_text = re.sub(r"[*_#]", "", text).strip()
    subprocess.run(["say", "-v", VOICE, "-r", VOICE_RATE, spoken_text], check=True)


def process_request(user_text: str, is_question: bool = True):
    global _bluetooth_info
    if "bluetooth" in user_text.lower() or "devices" in user_text.lower():
        _bluetooth_info = None
    return ask_ai(user_text, bluetooth_context(), is_question=is_question)


def main():
    print("Mac Alexa")
    bluetooth_info = bluetooth_context()
    print("\nDiscovered Bluetooth devices:")
    print(bluetooth_info)
    print("\nType a command. Type 'exit' to quit.")

    while True:
        try:
            user_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            break

        if "bluetooth" in user_text.lower() or "devices" in user_text.lower():
            bluetooth_info = bluetooth_context()

        try:
            answer = process_request(user_text, is_question=True)
            print(f"Assistant: {answer}")
            speak(answer)
        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
