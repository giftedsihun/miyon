"""Generate a Zundamon voice wav file through the local ttsclient server.

Usage:
    python generate_zundamon_wav.py --text "こんにちは" --output out.wav

Starts the ttsclient server if it is not already running, then posts the
text to the generateVoice REST endpoint and writes the returned wav bytes
to disk. See tts_service.py's transport helpers for the HTTP layer.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from tts_service import api_available, endpoint_privacy_notice, is_local_endpoint, speak_windows_native

from start_ttsclient_server import API_URL, start

VOICE_CHARACTER_SLOT_INDEX = 4  # Zundamon_official (voice character with reference voices)
REFERENCE_VOICE_SLOT_INDEX = 0  # bundled Zundamon reference voice


def generate_wav(text, output, language="all_ja", speed=1.0):
    payload = json.dumps(
        {
            "voice_character_slot_index": VOICE_CHARACTER_SLOT_INDEX,
            "reference_voice_slot_index": REFERENCE_VOICE_SLOT_INDEX,
            "text": text,
            "language": language,
            "speed": speed,
            "cutMethod": "No slice",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL + "/api/tts-manager/operation/generateVoice",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description="Generate Zundamon TTS wav via local ttsclient server")
    parser.add_argument("--text", default="こんにちは、私はずんだもんです。よろしくお願いします。", help="Japanese text to synthesize")
    parser.add_argument("--output", default="zundamon_output.wav", help="Path of the wav file to write")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed")
    args = parser.parse_args()

    if not is_local_endpoint(API_URL):
        print(endpoint_privacy_notice(API_URL), file=sys.stderr)
    print(endpoint_privacy_notice(API_URL))

    start()

    print(f"Generating voice for: {args.text}")
    data = generate_wav(args.text, args.output, speed=args.speed)
    output = Path(args.output)
    output.write_bytes(data)
    print(f"Saved {len(data)} bytes to {output}")


if __name__ == "__main__":
    main()
