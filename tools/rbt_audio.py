"""Extract the audio track of Sierra Robot (.RBT v5/v6, little endian) files to 22050 Hz mono WAV.

Port of ScummVM engines/sci/video/robot_decoder.cpp audio path, minus the ring buffer:
the stream is two interleaved DPCM16 channels (even/odd samples); each packet carries its
absolute position, and samples a channel already has are skipped (packet runway overlap).
Usage: python rbt_audio.py <in.rbt> <out.wav>   |   python rbt_audio.py <rbt_dir> <wav_dir>
"""
import array, os, struct, sys, wave

TABLE = [
    0x0000, 0x0008, 0x0010, 0x0020, 0x0030, 0x0040, 0x0050, 0x0060, 0x0070, 0x0080,
    0x0090, 0x00A0, 0x00B0, 0x00C0, 0x00D0, 0x00E0, 0x00F0, 0x0100, 0x0110, 0x0120,
    0x0130, 0x0140, 0x0150, 0x0160, 0x0170, 0x0180, 0x0190, 0x01A0, 0x01B0, 0x01C0,
    0x01D0, 0x01E0, 0x01F0, 0x0200, 0x0208, 0x0210, 0x0218, 0x0220, 0x0228, 0x0230,
    0x0238, 0x0240, 0x0248, 0x0250, 0x0258, 0x0260, 0x0268, 0x0270, 0x0278, 0x0280,
    0x0288, 0x0290, 0x0298, 0x02A0, 0x02A8, 0x02B0, 0x02B8, 0x02C0, 0x02C8, 0x02D0,
    0x02D8, 0x02E0, 0x02E8, 0x02F0, 0x02F8, 0x0300, 0x0308, 0x0310, 0x0318, 0x0320,
    0x0328, 0x0330, 0x0338, 0x0340, 0x0348, 0x0350, 0x0358, 0x0360, 0x0368, 0x0370,
    0x0378, 0x0380, 0x0388, 0x0390, 0x0398, 0x03A0, 0x03A8, 0x03B0, 0x03B8, 0x03C0,
    0x03C8, 0x03D0, 0x03D8, 0x03E0, 0x03E8, 0x03F0, 0x03F8, 0x0400, 0x0440, 0x0480,
    0x04C0, 0x0500, 0x0540, 0x0580, 0x05C0, 0x0600, 0x0640, 0x0680, 0x06C0, 0x0700,
    0x0740, 0x0780, 0x07C0, 0x0800, 0x0900, 0x0A00, 0x0B00, 0x0C00, 0x0D00, 0x0E00,
    0x0F00, 0x1000, 0x1400, 0x1800, 0x1C00, 0x2000, 0x3000, 0x4000,
]
# delta byte -> signed step
STEP = [TABLE[d] if d < 0x80 else -TABLE[d & 0x7F] for d in range(256)]
RATE = 22050
FRAME = 2048          # record alignment
ZERO_PAD = 2048       # kRobotZeroCompressSize
BLOCK_HEADER = 8      # kAudioBlockHeaderSize


def dedpcm16(data):
    out, s = [], 0
    for d in data:
        s += STEP[d]
        if s > 32767:
            s -= 65536
        elif s < -32768:
            s += 65536
        out.append(s)
    return out


def extract(path):
    """Return (samples: array('h'), frame_rate) or (None, rate) if the robot has no audio."""
    b = open(path, "rb").read()
    assert struct.unpack_from("<H", b, 0)[0] == 0x16 and b[2:6] == b"SOL\0", "not a robot"
    (version, block_size, primer_zero, _, n_frames, pal_size, primer_reserved,
     _, _, _has_pal, has_audio, _, frame_rate) = struct.unpack_from("<HHhHHHHhhBBHh", b, 6)
    assert version in (5, 6), f"robot version {version}"
    pos = 60
    packets = []  # (interleaved start index, compressed bytes)
    if has_audio and primer_reserved:
        _total, comp, even, odd = struct.unpack_from("<ihii", b, pos)
        assert comp == 0
        p = pos + 14
        packets.append((0, b[p:p + even]))
        packets.append((1, b[p + even:p + even + odd]))
    pos += primer_reserved  # ponytail: assumes reserved size covers primer header+data (true for Phantasmagoria)
    pos += pal_size
    fmt, w = ("<%dH", 2) if version == 5 else ("<%di", 4)
    video_sizes = struct.unpack_from(fmt % n_frames, b, pos); pos += w * n_frames
    record_sizes = struct.unpack_from(fmt % n_frames, b, pos); pos += w * n_frames
    pos += 256 * 4 + 256 * 2  # cue times + cue values
    pos += (-pos) % FRAME
    if not has_audio:
        return None, frame_rate
    expected = block_size - BLOCK_HEADER
    for i in range(n_frames):
        r = pos + video_sizes[i]
        apos, size = struct.unpack_from("<ii", b, r)
        if apos:
            data = b[r + 8:r + 8 + size]
            if size != expected:
                data = bytes(ZERO_PAD) + data
            packets.append((apos, data))
        pos += record_sizes[i]

    total = max(start + 2 * len(d) for start, d in packets)
    out = array.array("h", bytes(2 * total))
    written = [0, 1]  # next interleaved index each channel still needs
    for start, data in sorted(packets, key=lambda p: p[0]):
        ch = start & 1
        for k, s in enumerate(dedpcm16(data)):
            idx = start + 2 * k
            if idx >= written[ch]:
                out[idx] = s
        written[ch] = max(written[ch], start + 2 * len(data))
    return out, frame_rate


def write_wav(samples, path):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(samples.tobytes())


if __name__ == "__main__":
    assert dedpcm16(bytes([1, 0x81, 0x7F])) == [8, 0, 0x4000]
    src, dst = sys.argv[1], sys.argv[2]
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for f in sorted(os.listdir(src)):
            if not f.upper().endswith(".RBT"):
                continue
            out = os.path.join(dst, f[:-4] + ".wav")
            if os.path.exists(out):
                continue
            try:
                s, _ = extract(os.path.join(src, f))
            except Exception as e:  # keep going, report bad files
                print("FAIL", f, e); continue
            if s is None:
                print("noaudio", f); continue
            write_wav(s, out)
    else:
        s, fr = extract(src)
        print("frame rate", fr, "samples", None if s is None else len(s))
        if s is not None:
            write_wav(s, dst)
