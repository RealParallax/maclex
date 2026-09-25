# Mac Alexa

A small Python macOS voice assistant with a menu-bar push-to-talk button.

## What it does

- Lives in the macOS menu bar
- Click Start Listening and speak into your Mac microphone
- Click Stop Listening when you finish
- Sends the recording to Groq Whisper for speech-to-text
- Sends the transcript to a Groq chat model
- Speaks the answer with macOS say
- Uses the Mac's selected audio output, including a Bluetooth speaker
- Includes currently discovered BLE devices in the assistant context

The menu bar status changes between Ready, Listening, Transcribing, Thinking, and Speaking.

## Requirements

- macOS
- Python 3.11+
- A Groq API key
- Microphone access for the Python app
- A Bluetooth speaker is optional

## Setup

    cd mac-alexa
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt

Set your Groq key:

    export GROQ_API_KEY="your_key_here"

Optional settings:

    export GROQ_MODEL="openai/gpt-oss-120b"
    export GROQ_TRANSCRIPTION_MODEL="whisper-large-v3-turbo"
    export MAC_VOICE="Samantha"
    export MAC_VOICE_RATE="175"

Groq currently documents whisper-large-v3-turbo and whisper-large-v3 for speech-to-text. The menu-bar app defaults to the faster turbo model.

## Microphone permission

The first time macOS needs microphone access, allow it for the application launching Python.

If permission is denied, open:

System Settings -> Privacy & Security -> Microphone

Enable access for your Terminal/Python app.

## Run the menu-bar assistant

    source .venv/bin/activate
    export GROQ_API_KEY="your_key_here"
    python menu_bar.py

You should see a microphone icon in the menu bar.

Click it and choose Start Listening. Speak, then click Stop Listening. The app will transcribe your speech, ask Groq for an answer, and speak the response.

Keep the terminal open while running this development version so you can see errors and transcripts.

## Bluetooth output

Select your Bluetooth speaker under:

System Settings -> Sound -> Output

macOS say will use the currently selected audio output.

## Voice

The default macOS voice is Samantha:

    say -v Samantha -r 175 "Hello. This is my Mac assistant."

List installed voices with:

    say -v '?'

The voice is an Alexa-inspired assistant style, not Amazon's proprietary Alexa voice.

## Terminal mode

The text interface is still available:

    python assistant.py

## Next steps

Potential future improvements include a signed app bundle, launch-at-login support, a global keyboard push-to-talk shortcut, wake-word detection, conversation memory, and macOS controls.

Important: BLE discovery is not a complete inventory of every classic Bluetooth device connected to macOS. Audio speakers are commonly classic Bluetooth/A2DP devices, so BLE results should not be treated as the authoritative audio-device list.


## Desktop GUI

Run:

    source .venv/bin/activate
    export GROQ_API_KEY="your_key_here"
    python gui.py

The GUI replaces the terminal display with a simple desktop window. Type a request and click Ask. It then asks “Was this a question?” with Yes/No buttons before sending the request to Groq.

## Faster responses

The default chat model is `openai/gpt-oss-20b`, which Groq currently lists as a fast production model. You can override it with `GROQ_MODEL`. The voice wake listener also uses shorter default audio windows to reduce perceived latency.

## Terminal mode

You can still ask directly from the terminal:

    source .venv/bin/activate
    export GROQ_API_KEY="your_key_here"
    python assistant.py

The terminal mode sends the typed request directly to the assistant and speaks the answer.
