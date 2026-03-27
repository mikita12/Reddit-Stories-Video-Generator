import argparse
import os
from openai import OpenAI

client = OpenAI()


def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def clean_text(text):
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        line = line.strip()

        if line.startswith("HOOK:"):
            line = line.replace("HOOK:", "").strip()

        if line.startswith("SOURCE:"):
            break

        cleaned.append(line)

    text = " ".join(cleaned)

    text = text.replace('"', '')
    text = text.replace("'", "")

    return text.strip()


def generate_audio(text, output_file):
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="onyx",   # możesz zmienić: alloy, verse, etc.
        input=text,
    ) as response:
        response.stream_to_file(output_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    text = load_text(args.input)
    text = clean_text(text)

    print("[INFO] Generating audio...")
    generate_audio(text, args.output)

    print(f"[DONE] {args.output}")


if __name__ == "__main__":
    main()