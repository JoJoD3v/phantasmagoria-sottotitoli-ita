"""Transcribe every wav/<id>.wav into data/en/<id>.json (list of {start,end,text}).

wav/ (repo root, not committed) holds 16 kHz mono audio extracted from the game videos.
Usage: python transcribe.py [id ...]
"""
import glob, json, os, sys, site

# CUDA dlls shipped by the nvidia-* pip wheels
for sp in site.getsitepackages():
    for d in glob.glob(os.path.join(sp, "nvidia", "*", "bin")):
        os.add_dll_directory(d)
        os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]

from faster_whisper import WhisperModel

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
out_dir = os.path.join(base, "data", "en")
os.makedirs(out_dir, exist_ok=True)
model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")

MAX_CHARS, GAP = 60, 0.7


def split_segment(seg):
    """Whisper may merge a whole exchange into one segment: cut at pauses or every ~60 chars."""
    words = seg.words or []
    if not words:
        return [{"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()}]
    chunks, cur = [], []
    for w in words:
        if cur and (w.start - cur[-1].end > GAP or len("".join(x.word for x in cur)) > MAX_CHARS):
            chunks.append(cur); cur = []
        cur.append(w)
    chunks.append(cur)
    return [{"start": round(c[0].start, 2), "end": round(c[-1].end, 2),
             "text": "".join(x.word for x in c).strip()} for c in chunks]


files = sorted(glob.glob(os.path.join(base, "wav", "*.wav")))
if len(sys.argv) > 1:
    files = [f for f in files if os.path.basename(f)[:-4] in sys.argv[1:]]
for i, wav in enumerate(files):
    out = os.path.join(out_dir, os.path.basename(wav)[:-4] + ".json")
    if os.path.exists(out):
        continue
    segs, _ = model.transcribe(
        wav, language="en", beam_size=5, vad_filter=True,
        condition_on_previous_text=False,  # ponytail: avoids hallucination loops across silent gaps
        word_timestamps=True,
        initial_prompt="Adrienne Delaney, Don Gordon, Zoltan Carnovasch, Carno, Harriet, Cyrus, Malaria, Lou Ann, Mike Bartlett, Nyctasia.",
    )
    data = [c for s in segs for c in split_segment(s) if c["text"]]
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
    print(f"[{i + 1}/{len(files)}] {os.path.basename(wav)} {len(data)} seg", flush=True)
