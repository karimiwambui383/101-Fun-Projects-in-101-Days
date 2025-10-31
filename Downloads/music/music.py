#!/usr/bin/env python3
"""
orchestra_composer_fixed.py
🎵 Ultimate AI Orchestra Composer — Fixed for Windows Paths 🎵
"""

import os
import random
from midiutil import MIDIFile
import pygame
import subprocess
import shutil

# ===================== SETTINGS =====================
OUTPUT_DIR = "orchestra_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===================== INSTRUMENT MAP =====================
INSTRUMENTS = {
    "Strings": 48,      # String Ensemble 1
    "Brass": 61,        # Brass Section
    "Woodwinds": 73,    # Flute
    "Percussion": 118,  # Synth Drum
    "Piano": 0,         # Acoustic Grand Piano
    "Choir": 52,        # Choir Aahs
    "Synth": 81         # Lead 1 (square)
}

# ===================== GENRE CONFIGS =====================
GENRES = {
    "Cinematic / Movie Score": {"tempo": 90, "instruments": ["Strings", "Brass", "Percussion", "Choir"]},
    "Romantic / Ballad": {"tempo": 70, "instruments": ["Piano", "Strings", "Woodwinds"]},
    "Epic Battle": {"tempo": 110, "instruments": ["Brass", "Percussion", "Strings"]},
    "Ambient / Lo-Fi": {"tempo": 85, "instruments": ["Synth", "Piano", "Woodwinds"]},
    "Symphonic Pop / Modern Orchestra": {"tempo": 100, "instruments": ["Strings", "Piano", "Brass", "Percussion"]}
}

# ===================== FUNCTIONS =====================
def generate_orchestra_midi(genre, duration_bars=16, beats_per_bar=4, bars_per_phrase=4):
    config = GENRES[genre]
    tempo = config["tempo"]
    instruments = config["instruments"]

    midi = MIDIFile(len(instruments))
    for i, section in enumerate(instruments):
        midi.addTrackName(i, 0, section)
        midi.addTempo(i, 0, tempo)
        midi.addProgramChange(i, i, 0, INSTRUMENTS[section])

        time = 0
        for bar in range(duration_bars):
            note = random.randint(60, 80)
            duration = random.choice([0.25, 0.5, 1])
            velocity = random.randint(60, 100)
            midi.addNote(i, i, note, time, duration, velocity)
            time += duration

    # 💥 FIX: Sanitize filename for Windows
    safe_genre = "".join(c if c.isalnum() or c in (" ", "_") else "_" for c in genre)
    filename = os.path.join(OUTPUT_DIR, f"orchestra_{safe_genre.replace(' ', '_')}.mid")

    with open(filename, "wb") as f:
        midi.writeFile(f)
    print(f"✅ MIDI created: {filename}")
    return filename


def play_midi_with_pygame(filepath):
    pygame.init()
    pygame.mixer.init()
    print(f"\n🎧 Now playing: {filepath}\n")
    pygame.mixer.music.load(filepath)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.quit()


def convert_to_audio(filepath, soundfont="example.sf2"):
    wav_path = filepath.replace(".mid", ".wav")
    mp3_path = filepath.replace(".mid", ".mp3")

    if not os.path.exists(soundfont):
        print("⚠️ Missing SoundFont (.sf2)! Download one like 'FluidR3_GM.sf2' and place it here.")
        return

    subprocess.run(["fluidsynth", "-ni", soundfont, filepath, "-F", wav_path, "-r", "44100"])
    print(f"🎼 Exported WAV: {wav_path}")

    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-i", wav_path, mp3_path])
        print(f"🎧 Exported MP3: {mp3_path}")


# ===================== MAIN APP =====================
def main():
    print("\n🎻 Welcome to the AI Orchestra Composer 🎻\n")
    print("Choose your musical style:")
    for i, g in enumerate(GENRES.keys(), 1):
        print(f"  {i}. {g}")

    choice_num = int(input("\nEnter number (1–5): ") or 1)
    choice = list(GENRES.keys())[choice_num - 1]
    bars = int(input("How many bars? (Default 24): ") or 24)

    print(f"\n🎼 Composing {choice} piece ({bars} bars @ {GENRES[choice]['tempo']} BPM)...\n")
    midi_file = generate_orchestra_midi(choice, duration_bars=bars)
    play_midi_with_pygame(midi_file)
    convert_to_audio(midi_file)

    print("\n🚀 Composition complete — your orchestra is ready!\n")


if __name__ == "__main__":
    main()
