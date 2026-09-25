# Mac Alexa

A small Python starter project for a macOS voice assistant.

Current MVP:
- scans BLE devices using Bleak
- sends commands to a Groq-hosted model
- speaks responses using macOS `say`
- therefore uses whatever macOS audio output is currently selected, including a Bluetooth speaker

## 1. Requirements

- macOS
- Python 3.11+
- Homebrew (recommended)
- A Groq API key
- A Bluetooth speaker paired with your Mac

## 2. Create the environment

```bash
cd mac-alexa
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Configure your Groq API key

Export your Groq API key:

```bash
export GROQ_API_KEY="your_key_here"
```

Or add that export to your `~/.zshrc`.

By default, Mac Alexa uses `llama-3.3-70b-versatile`. You can override the model with:

```bash
export GROQ_MODEL="your_groq_model"
```

## 4. Bluetooth permission

Run:

```bash
python bluetooth_devices.py
```

macOS may ask Terminal/Python for Bluetooth access. Allow it.

If access was denied, go to:

System Settings → Privacy & Security → Bluetooth

and enable Bluetooth access for the app you are using to run Python.

Bleak's macOS backend uses Apple's CoreBluetooth APIs. macOS represents devices using UUIDs rather than normal Bluetooth MAC addresses, so the identifier shown by the script may not look like the address printed on the speaker.

## 5. Select the speaker

Before testing speech, select the Bluetooth speaker as the Mac's audio output:

System Settings → Sound → Output → your Bluetooth speaker

Then test:

```bash
say "Hello. This is my Mac assistant."
```

The voice should come through the selected output.

## 6. Start the assistant

```bash
source .venv/bin/activate
export GROQ_API_KEY="your_key_here"
python assistant.py
```

Try:

```text
What Bluetooth devices can you see?
What time is it?
Tell me a joke.
```

## What comes next

This is intentionally the first milestone rather than a fake "Alexa clone".

The next version should add:
1. microphone recording
2. speech-to-text
3. wake word detection ("Hey Mac")
4. tool/function calling
5. macOS controls such as opening apps and controlling volume
6. a small menu-bar application
7. automatic detection of the current audio output
8. conversation memory

Important: BLE discovery is not the same as a complete inventory of every classic Bluetooth device connected to macOS. Audio speakers are commonly classic Bluetooth/A2DP devices, so the next version should query macOS's audio system as well as CoreBluetooth.
