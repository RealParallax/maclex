import os
import subprocess

from groq import Groq
from bluetooth_devices import scan_bluetooth

SYSTEM_PROMPT = """You are a concise voice assistant running locally on a Mac.
Answer naturally and briefly because your response will be spoken aloud.
You can answer general questions. If the user asks about Bluetooth devices,
use the device information supplied by the application.
Do not claim to have performed an action unless the application actually did it.
"""

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


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
    # macOS 'say' uses the current system audio output, so if your Bluetooth
    # speaker is selected as the Mac's output, speech comes from that speaker.
    subprocess.run(["say", text], check=True)


def main():
    print("Mac Alexa")
    print("Scanning Bluetooth devices...")
    devices = scan_bluetooth()
    bluetooth_info = "\n".join(
        f"- {d['name'] or '(unnamed)'} [{d['address']}] RSSI={d['rssi']}"
        for d in devices
    ) or "No BLE devices were discovered."

    print("\nDiscovered Bluetooth devices:")
    print(bluetooth_info)

    print("\nType a command. Type 'exit' to quit.")
    print("For example: 'What Bluetooth devices can you see?'")
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
            devices = scan_bluetooth()
            bluetooth_info = "\n".join(
                f"- {d['name'] or '(unnamed)'} [{d['address']}] RSSI={d['rssi']}"
                for d in devices
            ) or "No BLE devices were discovered."

        try:
            answer = ask_ai(user_text, bluetooth_info)
            print(f"Assistant: {answer}")
            speak(answer)
        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
