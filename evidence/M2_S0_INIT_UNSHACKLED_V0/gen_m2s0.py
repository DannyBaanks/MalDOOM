"""Generate M2_S0_INIT EIR (deterministic).

Scope: initialize the derived core of Doom's S_0 inside the Unshackled VM.

stdin  : hex-framed bytes of one WAD THINGS lump, terminated by '.' (46).
         Each thing record is 10 bytes LE: x(i16) y(i16) angle(u16) type(u16)
         flags(u16). Framing is content-blind; every decode, scan and emit
         below executes in-VM.
VM does: hex-decode -> 10-byte record buffer -> census (things, type-1
         starts) -> capture the player-1 start x/y/angle -> emit
         "S0V1 x=<d> y=<signed> angle=<d> things=<d> p1=<d>\n".
Canonical startup constants (health/ammo/...) are part of the game's state
DEFINITION, not derived data; they are recorded in run.json, not in-VM.

EIR values are 24-bit (same bound as M1/M2a): all fields fit (|x|<32768,
angles <65536, counts <2^24).
"""
import json
import pathlib
import struct
import sys

RET = 2000          # call/return slot for the hex decoder
BUF = 3000          # 10-byte thing-record buffer
RIDX = 3100         # bytes collected in the current record
THINGS = 3101       # total records seen
P1 = 3102           # player-1 starts seen
PX = 3103
PY = 3104
PANGLE = 3105


def gen(wad: pathlib.Path, lump_name: str, out_dir: pathlib.Path) -> dict:
    data = wad.read_bytes()
    magic, numlumps, diroff = struct.unpack("<4sII", data[:12])
    assert magic == b"IWAD", magic
    entries = []
    for i in range(numlumps):
        off = diroff + i * 16
        pos, size, name = struct.unpack("<II8s", data[off:off + 16])
        entries.append((name.rstrip(b"\0").decode(), pos, size))
    e1m1 = next(i for i, e in enumerate(entries) if e[0] == lump_name)
    things_idx = next(i for i in range(e1m1, len(entries)) if entries[i][0] == "THINGS")
    tname, tpos, tsize = entries[things_idx]
    blob = data[tpos:tpos + tsize]
    assert len(blob) == tsize and tsize % 10 == 0

    # ---- EIR -------------------------------------------------------------
    L = []
    L.append("# M2_S0_INIT: stdin = hex-framed THINGS lump bytes + '.' terminator.")
    L.append("# VM decodes, walks 10-byte thing records, censuses and captures the")
    L.append("# player-1 start, then emits S0V1 x y angle things p1.")
    L.append(f"# Layout: RET={RET}; BUF={BUF}..{BUF + 9}; RIDX={RIDX}; "
             f"THINGS={THINGS}; P1={P1}; PX={PX}; PY={PY}; PANGLE={PANGLE}.")
    L.append("jmp main")

    # hexpair: two hex chars in A/B (already fetched) -> byte in D, returns.
    # '.' is not hex; the caller checks for it before calling.
    L.append("hexpair:")
    L.append("jlt hex_hi09, A, 48")
    L.append("jgt hex_hiAF, A, 57")
    L.append("sub A, 48")
    L.append("jmp hex_hidone")
    L.append("hex_hiAF:")
    L.append("jlt hex_hierr, A, 65")
    L.append("jgt hex_hiAF2, A, 70")
    L.append("sub A, 55")
    L.append("jmp hex_hidone")
    L.append("hex_hiAF2:")
    L.append("jlt hex_hierr, A, 97")
    L.append("jgt hex_hierr, A, 102")
    L.append("sub A, 87")
    L.append("jmp hex_hidone")
    L.append("hex_hidone:")
    L.append("mov D, A")
    for _ in range(4):
        L.append("add D, D")
    L.append("jlt hex_lo09, B, 48")
    L.append("jgt hex_loAF, B, 57")
    L.append("sub B, 48")
    L.append("jmp hex_lodone")
    L.append("hex_loAF:")
    L.append("jlt hex_loerr, B, 65")
    L.append("jgt hex_loAF2, B, 70")
    L.append("sub B, 55")
    L.append("jmp hex_lodone")
    L.append("hex_loAF2:")
    L.append("jlt hex_loerr, B, 97")
    L.append("jgt hex_loerr, B, 102")
    L.append("sub B, 87")
    L.append("hex_lodone:")
    L.append("add D, B")
    L.append("load C, %d" % RET)
    L.append("jmp C")
    L.append("hex_hi09:")
    L.append("hex_lo09:")
    L.append("hex_hierr:")
    L.append("hex_loerr:")
    L.append("putc 69")          # 'E'
    L.append("putc 10")
    L.append("exit")

    L.append("main:")
    for slot in (RIDX, THINGS, P1, PX, PY, PANGLE):
        L.append("mov A, 0")
        L.append("store A, %d" % slot)
    L.append("byte_loop:")
    L.append("getc A")
    L.append("jeq finish, A, 46")     # '.' terminator
    L.append("getc B")
    L.append("mov C, byte_ret")
    L.append("store C, %d" % RET)
    L.append("jmp hexpair")
    L.append("byte_ret:")
    L.append("load A, %d" % RIDX)     # current index within the record
    L.append("add A, %d" % BUF)
    L.append("store D, A")
    L.append("load A, %d" % RIDX)
    L.append("add A, 1")
    L.append("store A, %d" % RIDX)
    L.append("jlt byte_loop, A, 10")
    # --- record complete ---
    L.append("mov A, 0")
    L.append("store A, %d" % RIDX)
    L.append("load A, %d" % THINGS)
    L.append("add A, 1")
    L.append("store A, %d" % THINGS)
    # type = mem[BUF+6] + mem[BUF+7]*256
    L.append("mov A, %d" % (BUF + 6))
    L.append("load B, A")
    L.append("mov A, %d" % (BUF + 7))
    L.append("load A, A")
    for _ in range(8):
        L.append("add A, A")
    L.append("add A, B")
    L.append("jne record_done, A, 1")
    # player-1 start: capture x, y(raw), angle
    L.append("load A, %d" % P1)
    L.append("add A, 1")
    L.append("store A, %d" % P1)
    L.append("mov A, %d" % BUF)
    L.append("load B, A")
    L.append("mov A, %d" % (BUF + 1))
    L.append("load A, A")
    for _ in range(8):
        L.append("add A, A")
    L.append("add A, B")
    L.append("store A, %d" % PX)
    L.append("mov A, %d" % (BUF + 2))
    L.append("load B, A")
    L.append("mov A, %d" % (BUF + 3))
    L.append("load A, A")
    for _ in range(8):
        L.append("add A, A")
    L.append("add A, B")
    L.append("store A, %d" % PY)
    L.append("mov A, %d" % (BUF + 4))
    L.append("load B, A")
    L.append("mov A, %d" % (BUF + 5))
    L.append("load A, A")
    for _ in range(8):
        L.append("add A, A")
    L.append("add A, B")
    L.append("store A, %d" % PANGLE)
    L.append("record_done:")
    L.append("jmp byte_loop")

    # ---- emit ------------------------------------------------------------
    L.append("finish:")
    L.append("load A, %d" % RIDX)
    L.append("jeq finish_ok, A, 0")
    L.append("putc 80")          # 'P' partial record at terminator
    L.append("putc 10")
    L.append("exit")
    L.append("finish_ok:")

    def emit_lit(chars):
        for ch in chars:
            L.append("putc %d" % ord(ch))

    def emit_dec(addr, tag):
        """Print the unsigned decimal value at addr (<= 6 digits)."""
        L.append("mov A, %d" % addr)
        L.append("load A, A")
        L.append("mov B, 0")                       # leading-zero suppression
        for div in (100000, 10000, 1000, 100, 10):
            L.append("mov D, 0")
            L.append("%s_d%d:" % (tag, div))
            L.append("jlt %s_e%d, A, %d" % (tag, div, div))
            L.append("sub A, %d" % div)
            L.append("add D, 1")
            L.append("jmp %s_d%d" % (tag, div))
            L.append("%s_e%d:" % (tag, div))
            L.append("jgt %s_w%d, D, 0" % (tag, div))
            L.append("jgt %s_w%d, B, 0" % (tag, div))
            L.append("jmp %s_n%d" % (tag, div))
            L.append("%s_w%d:" % (tag, div))
            L.append("add D, 48")
            L.append("putc D")
            L.append("mov B, 1")
            L.append("%s_n%d:" % (tag, div))
        L.append("add A, 48")
        L.append("putc A")

    def emit_signed(addr, tag):
        L.append("mov A, %d" % addr)
        L.append("load A, A")
        L.append("jlt %s_pos, A, 32768" % tag)
        L.append("putc 45")                        # '-'
        L.append("mov D, 65536")
        L.append("sub D, A")
        L.append("mov A, D")
        L.append("%s_pos:" % tag)
        L.append("mov B, 0")
        for div in (100000, 10000, 1000, 100, 10):
            L.append("mov D, 0")
            L.append("%s_d%d:" % (tag, div))
            L.append("jlt %s_e%d, A, %d" % (tag, div, div))
            L.append("sub A, %d" % div)
            L.append("add D, 1")
            L.append("jmp %s_d%d" % (tag, div))
            L.append("%s_e%d:" % (tag, div))
            L.append("jgt %s_w%d, D, 0" % (tag, div))
            L.append("jgt %s_w%d, B, 0" % (tag, div))
            L.append("jmp %s_n%d" % (tag, div))
            L.append("%s_w%d:" % (tag, div))
            L.append("add D, 48")
            L.append("putc D")
            L.append("mov B, 1")
            L.append("%s_n%d:" % (tag, div))
        L.append("add A, 48")
        L.append("putc A")

    emit_lit("S0V1 x=")
    emit_signed(PX, "x")
    emit_lit(" y=")
    emit_signed(PY, "y")
    emit_lit(" angle=")
    emit_dec(PANGLE, "ang")
    emit_lit(" things=")
    emit_dec(THINGS, "th")
    emit_lit(" p1=")
    emit_dec(P1, "p1")
    emit_lit("\n")
    L.append("exit")

    text = "\n".join(L) + "\n"

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "source.eir").write_text(text, encoding="utf-8")
    hexed = blob.hex() + "."
    (out_dir / ("stdin_%s.hex" % lump_name)).write_text(hexed, encoding="utf-8")

    starts = []
    for i in range(tsize // 10):
        x, y, ang, typ, flags = struct.unpack("<hhHHH", blob[i * 10:i * 10 + 10])
        if typ == 1:
            starts.append({"x": x, "y": y, "angle": ang})
    return {
        "lump": tname,
        "map": lump_name,
        "dir_index": e1m1,
        "things_index": things_idx,
        "filepos": tpos,
        "size": tsize,
        "records": tsize // 10,
        "player1_starts": starts,
        "expected_text": "S0V1 x=%d y=%d angle=%d things=%d p1=%d\n" % (
            starts[0]["x"], starts[0]["y"], starts[0]["angle"],
            tsize // 10, len(starts)) if len(starts) == 1 else None,
        "hex_chars": len(hexed),
    }


if __name__ == "__main__":
    wad = pathlib.Path(sys.argv[1])
    slice_name = sys.argv[2]              # e.g. E1M1
    out = pathlib.Path(sys.argv[3])
    info = gen(wad, slice_name, out)
    print(json.dumps(info, indent=2))
