import os
import yt_dlp

print("=== 🎬 Media Fetcher – Powered by yt-dlp ===")

url = input("Paste your link here: ").strip()

print("\n🎵 Choose your download format:")
print("1️⃣  MP3 (audio only)")
print("2️⃣  WAV (audio only, lossless)")
print("3️⃣  MP4 (full video)")
choice = input("Enter 1, 2, or 3: ").strip()

formats = {
    "1": "mp3",
    "2": "wav",
    "3": "mp4"
}

if choice not in formats:
    print("⚠️ Invalid option. Exiting...")
    exit()

selected = formats[choice]

ydl_opts = {
    "ignoreerrors": True,
    "no_warnings": True,
    "outtmpl": "%(title)s.%(ext)s",
    "noplaylist": True  # ✅ prevents playlist auto-download
}

# ✅ Audio extraction settings when mp3 or wav is chosen
if selected in ["mp3", "wav"]:
    ydl_opts["format"] = "bestaudio/best"
    ydl_opts["postprocessors"] = [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": selected,
        "preferredquality": "192"
    }]
else:
    ydl_opts["format"] = "bestvideo+bestaudio/best"

print(f"\n🎧 Downloading as {selected.upper()}...")
print("⬇️ Starting download...\n")

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print("\n✅ Download complete. Mission accomplished!")
except Exception as e:
    print(f"\n💥 Error: {e}")
