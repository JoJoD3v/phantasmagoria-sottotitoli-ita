"""Extract the speech clips of RESOURCE.AUD (SCI32 audio maps) to WAV.

Names match the patched ScummVM lookup:
  plain audio  n                          -> <n>.aud.wav
  audio36      map, noun/verb/cond/seq    -> <map>-<tuple %08X>.a36.wav
Map patch files (<n>.MAP in the game dir or PATCHES/) override the copies in RESSCI.000,
same as in ScummVM. Usage: python aud_extract.py <game Phant dir> <out dir>
"""
import os, struct, subprocess, sys, tempfile


def read_maps(game):
    maps = {}
    m = open(os.path.join(game, "RESMAP.000"), "rb").read()
    types, i = [], 0
    while m[i] != 0xFF:
        types.append((m[i], struct.unpack_from("<H", m, i + 1)[0])); i += 3
    types.append((0xFF, struct.unpack_from("<H", m, i + 1)[0]))
    with open(os.path.join(game, "RESSCI.000"), "rb") as r:
        for k, (t, start) in enumerate(types[:-1]):
            if t != 0x10:  # kResourceTypeMap
                continue
            for p in range(start, types[k + 1][1], 6):
                n, off = struct.unpack_from("<HI", m, p)
                r.seek(off)
                _, _, packed, _, comp = struct.unpack("<BHIIH", r.read(13))
                assert comp == 0, "compressed map"
                maps[n] = r.read(packed)
    for d in (game, os.path.join(game, "PATCHES")):
        for f in os.listdir(d) if os.path.isdir(d) else []:
            if f.upper().endswith(".MAP") and f[:-4].isdigit():
                data = open(os.path.join(d, f), "rb").read()
                maps[int(f[:-4])] = data[2 + data[1]:]  # skip patch header
    return maps


def parse(num, data):
    """Yield (name, offset, sync_size). Port of ResourceManager::readAudioMapSCI11 (SCI32 branch)."""
    p = 0
    if num == 65535:
        off = 0
        while p + 2 <= len(data):
            n = struct.unpack_from("<H", data, p)[0]; p += 2
            if n == 0xFFFF:
                break
            off += int.from_bytes(data[p:p + 3], "little"); p += 3
            yield f"{n}.aud", off, 0
        return
    off = struct.unpack_from("<I", data, 0)[0]; p = 4
    while p + 4 <= len(data):
        n = struct.unpack_from(">I", data, p)[0]; p += 4
        if n & 0xFF == 0xFF:
            break
        off += int.from_bytes(data[p:p + 3], "little"); p += 3
        sync = 0
        if n & 0x80:
            sync = struct.unpack_from("<H", data, p)[0]; p += 2
        yield f"{num}-{n & 0xFFFFFF3F:08X}.a36", off, sync


def main(game, out):
    os.makedirs(out, exist_ok=True)
    aud = open(os.path.join(game, "RESOURCE.AUD"), "rb").read()
    count = 0
    for num, data in sorted(read_maps(game).items()):
        for name, off, sync in parse(num, data):
            start = off + sync
            if aud[start:start + 1] != b"\x8D" or aud[start + 2:start + 6] != b"SOL\0":
                print("skip", name, "no SOL header at", start); continue
            hsize = aud[start + 1]
            size = struct.unpack_from("<I", aud, start + 9)[0]
            with tempfile.NamedTemporaryFile(suffix=".sol", delete=False) as t:
                t.write(aud[start:start + 2 + hsize + size])
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", t.name, "-ac", "1", "-ar", "16000",
                            os.path.join(out, name + ".wav")], check=True)
            os.unlink(t.name)
            count += 1
    print("clip estratti:", count)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
