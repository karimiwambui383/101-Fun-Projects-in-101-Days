#!/usr/bin/env python3
"""
orchestra_studio.py
All-in-one lightweight orchestra studio:
- multi-genre, multi-personality composer
- sections (intro/verse/build/drop/outro)
- multi-instrument orchestration
- humanization, dynamics, call-and-response
- exports: MIDI (.mid), WAV (.wav via fluidsynth), MP3 (.mp3 via ffmpeg)
- JSON spec export describing what was composed
"""

import os, sys, random, math, json, shutil, subprocess, time
from datetime import datetime
from midiutil import MIDIFile

# try optional modules
try:
    import pygame
except Exception:
    pygame = None
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

# -------------------------
# Config / Instruments map
# -------------------------
OUTPUT_DIR = "orchestra_studio_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SOUNDFONT_CANDIDATES = ["FluidR3_GM.sf2", "GeneralUser_GS_SoftSynth_v1.44.sf2", "Orchestral.sf2", "example.sf2"]

# General MIDI program numbers (a short useful subset)
GM = {
    "acoustic_grand_piano": 0,
    "bright_acoustic_piano": 1,
    "honkytonk": 3,
    "electric_piano": 4,
    "harpsichord": 6,
    "drawbar_organ": 16,
    "acoustic_guitar_nylon": 24,
    "electric_bass_finger": 33,
    "violin": 40,
    "viola": 41,
    "cello": 42,
    "contrabass": 43,
    "tremolo_strings": 46,
    "synth_strings_1": 50,
    "choir_aahs": 52,
    "trumpet": 56,
    "trombone": 57,
    "french_horn": 60,
    "soprano_sax": 64,
    "flute": 73,
    "clarinet": 71,
    "timpani": 47,
    "pad_1_new_age": 88,
    "fx_1_rain": 95
}
PERCUSSION_CHANNEL = 9  # MIDI channel 10 (0-based 9) is percussion

# -------------------------
# Scales & chord helpers
# -------------------------
MAJOR = [0,2,4,5,7,9,11]
MINOR = [0,2,3,5,7,8,10]
DORIAN = [0,2,3,5,7,9,10]
PENTATONIC = [0,2,4,7,9]

def transpose_scale(root, mode):
    return [root + step for step in mode]

def build_chord_from_scale(scale, degree, kind="triad"):
    root = scale[degree % len(scale)]
    if kind == "triad":
        third = scale[(degree+2)%len(scale)]
        fifth = scale[(degree+4)%len(scale)]
        return [root, third, fifth]
    if kind == "maj7":
        third = scale[(degree+2)%len(scale)]
        fifth = scale[(degree+4)%len(scale)]
        seventh = scale[(degree+6)%len(scale)]
        return [root, third, fifth, seventh]
    if kind == "sus2":
        return [root, scale[(degree+1)%len(scale)], scale[(degree+4)%len(scale)]]
    # fallback triad
    return [root, scale[(degree+2)%len(scale)], scale[(degree+4)%len(scale)]]

def clamp(v, a, b): return max(a, min(b, v))

# -------------------------
# Styles and personalities
# -------------------------
STYLE_PRESETS = {
    "Cinematic / Movie Score": {"root":60, "mode":MAJOR, "bpm":95},
    "Romantic / Ballad": {"root":64, "mode":MINOR, "bpm":70},
    "Epic / Battle": {"root":48, "mode":MINOR, "bpm":120},
    "Ambient / Lo-Fi": {"root":55, "mode":PENTATONIC, "bpm":60},
    "Symphonic Pop / Modern Orchestra": {"root":60, "mode":MAJOR, "bpm":100},
    "Ballad Orchestra": {"root":62, "mode":MINOR, "bpm":72},
    "Romantic Orchestra": {"root":60, "mode":MINOR, "bpm":78},
    "Trailer / Epic Hybrid": {"root":50, "mode":MINOR, "bpm":105},
    "Neo-Jazz Lounge": {"root":60, "mode":DORIAN, "bpm":85},
    "Cinematic Ambient": {"root":57, "mode":PENTATONIC, "bpm":50}
}

PERSONALITIES = {
    "Mozart Mode": {"tightness":0.02, "complexity":0.6, "swing":0.0, "velocity_base":85},
    "Hans Zimmer Mode": {"tightness":0.04, "complexity":0.9, "swing":0.02, "velocity_base":96},
    "Billie Eilish Mode": {"tightness":0.03, "complexity":0.4, "swing":0.04, "velocity_base":70},
    "AI Lost in Space": {"tightness":0.08, "complexity":0.95, "swing":0.08, "velocity_base":78},
    "Default Composer": {"tightness":0.05, "complexity":0.7, "swing":0.02, "velocity_base":82}
}

# -------------------------
# Orchestra layout (tracks)
# -------------------------
ORCHESTRA_LAYOUT = [
    ("Piano/Harp", GM["acoustic_grand_piano"], 0),
    ("High Strings (Violins)", GM["violin"], 1),
    ("Low Strings (Cello/Viola)", GM["cello"], 2),
    ("Woodwinds", GM["flute"], 3),
    ("Brass", GM["french_horn"], 4),
    ("Bass", GM["electric_bass_finger"], 5),
    ("Choir/Pad", GM["choir_aahs"], 6),
    ("Percussion", None, PERCUSSION_CHANNEL),
    ("Synth/Texture", GM["pad_1_new_age"], 7)
]

# -------------------------
# Utility: sanitize filename
# -------------------------
def sanitize_filename(s):
    safe = "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in s)
    return "_".join(safe.split())

# -------------------------
# Humanization & dynamics
# -------------------------
def humanize_time(t, tightness):
    return t + random.uniform(-tightness, tightness)

def velocity_for_phase(phase, base, variance=20):
    # phase 0..1 across a phrase
    v = base + int(math.sin(math.pi * phase) * variance)
    return clamp(v, 20, 127)

# -------------------------
# Song section generators
# -------------------------
def generate_phrase(midi, track_idx, channel, scale, start_beat, beats, personality, role="lead"):
    """Generates a phrase for a given instrument track."""
    base = PERSONALITIES[personality]["velocity_base"]
    tight = PERSONALITIES[personality]["tightness"]
    complexity = PERSONALITIES[personality]["complexity"]
    chance_note = 0.9 if role=="lead" else 0.5
    t = start_beat
    placed = []
    for i in range(int(beats*2)):  # step in 0.5 beat increments
        if random.random() < chance_note * complexity:
            pitch = random.choice(scale) + (0 if role!="bass" else -24)
            dur = random.choice([0.5, 1.0, 0.25])
            phase = (i / (beats*2))
            vel = velocity_for_phase(phase, base, variance=int(20*complexity))
            human_t = humanize_time(t, tight)
            midi.addNote(track_idx, channel, int(pitch), human_t, dur, vel)
            placed.append((int(pitch), human_t, dur, vel))
        t += 0.5
    return placed

# -------------------------
# Core: compose full piece
# -------------------------
def compose_full_piece(title, style, personality, bars=24, beats_per_bar=4, sections=None):
    preset = STYLE_PRESETS[style]
    root = preset["root"]
    mode = preset["mode"]
    bpm = preset["bpm"]
    if PERSONALITIES.get(personality) is None:
        personality = "Default Composer"

    scale = transpose_scale(root, mode)
    total_beats = bars * beats_per_bar

    midi = MIDIFile(len(ORCHESTRA_LAYOUT))
    for ti, (name, program, chan) in enumerate(ORCHESTRA_LAYOUT):
        midi.addTrackName(ti, 0, name)
        midi.addTempo(ti, 0, bpm)
        if program is not None:
            midi.addProgramChange(ti, chan, 0, program)

    # build sections if not provided
    if not sections:
        # a typical structure: intro (4), verse (8), build (4), drop (6), outro (2)
        sections = [
            ("intro", 4), ("verse", 8), ("build", 4), ("drop", 6), ("outro", max(2, bars-22))
        ]
    # ensure total bars match
    sec_total = sum(length for _,length in sections)
    if sec_total != bars:
        # scale proportionally (simple rebalance)
        factor = bars / sec_total
        sections = [(name, max(1, int(length*factor))) for name,length in sections]

    beat_cursor = 0
    metadata = {"title": title, "style": style, "personality": personality, "bpm": bpm, "sections": []}

    # motif storage for call-and-response
    motifs = []

    for sec_name, sec_bars in sections:
        sec_beats = sec_bars * beats_per_bar
        meta_sec = {"name": sec_name, "bars": sec_bars, "start_beat": beat_cursor}
        # instrumentation intensity control
        intensity = {"intro":0.4, "verse":0.7, "build":0.9, "drop":1.0, "outro":0.5}.get(sec_name, 0.7)

        # for each instrument track, generate phrases
        for ti, (iname, program, chan) in enumerate(ORCHESTRA_LAYOUT):
            role = "lead" if "Violins" in iname or "Piano" in iname else ("bass" if "Bass" in iname else "harmony")
            # reduce note density for lower intensity
            if random.random() < (0.2 + (1.0-intensity)*0.7): 
                # sometimes skip to create dynamics
                continue

            # multiplier for phrase length (longer for pads)
            phrase_beats = sec_beats if "Pad" in iname or "Choir" in iname else min(sec_beats, 8)
            placed_notes = generate_phrase(midi, ti, chan, scale, beat_cursor, phrase_beats, personality, role=role)
            # pick a motif occasionally
            if role=="lead" and random.random() < 0.6:
                motifs.append((placed_notes, iname))

        # occasional modulation / tension
        if sec_name in ("build", "drop") and random.random() < 0.4:
            shift = random.choice([2, -1, 5, -3])
            root += shift
            scale = transpose_scale(root, mode)
            # add timpani hit marker on percussion track
            perct = next(i for i,(n,p,ch) in enumerate(ORCHESTRA_LAYOUT) if "Percussion" in n)
            midi.addNote(perct, PERCUSSION_CHANNEL, 47, beat_cursor + 0.0, 1.0, 120)

        meta_sec["intensity"] = intensity
        metadata["sections"].append(meta_sec)
        beat_cursor += sec_beats

    # call-and-response: take first motif create echo
    if motifs:
        motif, instrument = random.choice(motifs)
        # schedule response on another track a little later
        for (p, s, d, v) in motif[:min(8, len(motif))]:
            # pick a target track (woodwinds or brass)
            target_t = 3 if random.random() < 0.6 else 4
            resp_start = s + random.uniform(1.0, 2.0)
            midi.addNote(target_t, ORCHESTRA_LAYOUT[target_t][2], int(p + random.choice([-12,7,0])), resp_start, d, clamp(v-8, 30, 110))

    # finalize file
    safe_title = sanitize_filename(title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    midi_fname = os.path.join(OUTPUT_DIR, f"{safe_title}_{timestamp}.mid")
    with open(midi_fname, "wb") as f:
        midi.writeFile(f)

    # write JSON spec
    json_spec = os.path.join(OUTPUT_DIR, f"{safe_title}_{timestamp}.json")
    with open(json_spec, "w", encoding="utf-8") as jf:
        json.dump(metadata, jf, indent=2)

    return midi_fname, json_spec, bpm

# -------------------------
# Rendering helpers
# -------------------------
def find_soundfont():
    cwd = os.getcwd()
    for cand in SOUNDFONT_CANDIDATES:
        path = os.path.join(cwd, cand)
        if os.path.exists(path):
            return path
    # search any .sf2
    for f in os.listdir(cwd):
        if f.lower().endswith(".sf2"):
            return os.path.join(cwd, f)
    return None

def render_mid_to_wav(sf, mid_path, wav_path):
    if not shutil.which("fluidsynth"):
        print("⚠ fluidsynth CLI not found. Skipping render to WAV. Install FluidSynth.")
        return False
    cmd = ["fluidsynth", "-ni", sf, mid_path, "-F", wav_path, "-r", "44100"]
    print("render cmd:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    return True

def wav_to_mp3(wav_path, mp3_path):
    if not shutil.which("ffmpeg"):
        print("⚠ ffmpeg not found; skipping MP3 conversion.")
        return False
    cmd = ["ffmpeg", "-y", "-i", wav_path, mp3_path]
    subprocess.run(cmd, check=True)
    return True

# -------------------------
# Playback (wav) using pygame
# -------------------------
def play_audio_file(path):
    if not pygame:
        print("pygame not installed; cannot auto-play audio.")
        return
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass
    print("▶ Playing", path)
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(30)
    pygame.mixer.quit()
    pygame.quit()

# -------------------------
# CLI + optional GUI
# -------------------------
def run_cli():
    print("\n--- ORCHESTRA STUDIO (CLI) ---\n")
    print("pick a style:")
    keys = list(STYLE_PRESETS.keys())
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {k} (suggested BPM: {STYLE_PRESETS[k]['bpm']})")
    choice = input("choice (1-{}): ".format(len(keys))).strip() or "1"
    try:
        idx = int(choice)-1
        style = keys[idx]
    except Exception:
        style = keys[0]

    print("\npersonalities:")
    per_keys = list(PERSONALITIES.keys())
    for i,k in enumerate(per_keys,1):
        print(f"  {i}. {k}")
    p_choice = input("personality (1-{}): ".format(len(per_keys))).strip() or "5"
    try:
        ps = per_keys[int(p_choice)-1]
    except:
        ps = "Default Composer"

    title = input("title for this piece (or press Enter to auto): ").strip()
    if not title:
        title = f"{style.split('/')[0].strip()}_{ps.replace(' ','_')}"

    bars = input("how many bars? (default 24): ").strip() or "24"
    try:
        bars = int(bars)
    except:
        bars = 24

    midi_path, json_spec, bpm = compose_full_piece(title, style, ps, bars)
    print("\nMIDI created at:", midi_path)
    print("JSON spec at:", json_spec)

    sf = find_soundfont()
    if not sf:
        print("\nNo soundfont auto-detected. Place a .sf2 in folder or provide path.")
        sf_input = input("enter path to .sf2 (or press Enter to skip audio render): ").strip()
        if sf_input:
            sf = sf_input
    if sf:
        wav = midi_path.replace(".mid",".wav")
        print("Rendering WAV to:", wav)
        try:
            ok = render_mid_to_wav(sf, midi_path, wav)
            if ok:
                print("WAV rendered:", wav)
                mp3 = midi_path.replace(".mid",".mp3")
                wav_to_mp3(wav, mp3)
                print("MP3:", mp3)
                play_now = input("play the WAV now? (y/N): ").strip().lower()
                if play_now == "y":
                    play_audio_file(wav)
        except subprocess.CalledProcessError as e:
            print("rendering error:", e)
    print("\nDone. Check", OUTPUT_DIR, "for outputs.")

def run_gui():
    # minimal GUI wrapper to pick options and run composer
    root = tk.Tk()
    root.title("Orchestra Studio")
    frm = ttk.Frame(root, padding=12)
    frm.grid()

    ttk.Label(frm, text="Orchestra Studio", font=("Helvetica", 16, "bold")).grid(column=0, row=0, columnspan=3, pady=6)
    ttk.Label(frm, text="Style:").grid(column=0, row=1, sticky="w")
    style_var = tk.StringVar(value=list(STYLE_PRESETS.keys())[0])
    style_cb = ttk.Combobox(frm, textvariable=style_var, values=list(STYLE_PRESETS.keys()), width=40)
    style_cb.grid(column=1, row=1, columnspan=2)

    ttk.Label(frm, text="Personality:").grid(column=0, row=2, sticky="w")
    per_var = tk.StringVar(value=list(PERSONALITIES.keys())[0])
    per_cb = ttk.Combobox(frm, textvariable=per_var, values=list(PERSONALITIES.keys()), width=40)
    per_cb.grid(column=1, row=2, columnspan=2)

    ttk.Label(frm, text="Title:").grid(column=0, row=3, sticky="w")
    title_var = tk.StringVar(value="")
    ttk.Entry(frm, textvariable=title_var, width=44).grid(column=1, row=3, columnspan=2)

    ttk.Label(frm, text="Bars:").grid(column=0, row=4, sticky="w")
    bars_var = tk.IntVar(value=24)
    ttk.Spinbox(frm, from_=4, to=256, textvariable=bars_var).grid(column=1, row=4, sticky="w")

    status = tk.StringVar(value="Ready")

    def on_compose():
        status.set("Composing...")
        root.update()
        t = title_var.get().strip() or f"{style_var.get().split('/')[0].strip()}_{per_var.get().replace(' ','_')}"
        midi_path, json_path, bpm = compose_full_piece(t, style_var.get(), per_var.get(), bars_var.get())
        status.set(f"MIDI created: {os.path.basename(midi_path)}")
        msg = f"Created MIDI: {midi_path}\nJSON: {json_path}\nOpen output folder?"
        if messagebox.askyesno("Done", msg):
            os.startfile(os.path.abspath(OUTPUT_DIR)) if sys.platform.startswith("win") else subprocess.run(["xdg-open", OUTPUT_DIR])
        status.set("Ready")

    ttk.Button(frm, text="Compose", command=on_compose).grid(column=0, row=5, pady=8)
    ttk.Label(frm, textvariable=status).grid(column=1, row=5, columnspan=2)
    root.mainloop()

# -------------------------
# Entry point
# -------------------------
def main():
    print("orchestra_studio.py — mini-orchestra composer")
    if TK_AVAILABLE:
        choice = input("Launch GUI? (Y/n): ").strip().lower() or "y"
        if choice == "y":
            try:
                run_gui()
                return
            except Exception as e:
                print("GUI failed (falling back to CLI):", e)
    run_cli()

if __name__ == "__main__":
    main()
