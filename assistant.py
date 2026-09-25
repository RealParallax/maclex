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
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
VOICE = os.environ.get("MAC_VOICE", "Samantha")
VOICE_RATE = os.environ.get("MAC_VOICE_RATE", "175")


def bluetooth_context() -> str:
    devices = scan_bluetooth()
    return "\n".join(
        f"- {d['name'] or '(unnamed)'} [{d['address']}] RSSI={d['rssi']}"
        for d in devices
    ) or "No BLE devices were discovered."


def ask_ai(user_text: str, bluetooth_info: str) -> str:
    prompt = f"""Bluetooth information from this Mac:

{bluetooth_info}

User request:
{user_text}
"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def speak(text: str):
    spoken_text = re.sub(r"[*_#]", "", text).strip()
    subprocess.run(["say", "-v", VOICE, "-r", VOICE_RATE, spoken_text], check=True)


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
            answer = ask_ai(user_text, bluetooth_info)
            print(f"Assistant: {answer}")
            speak(answer)
        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
