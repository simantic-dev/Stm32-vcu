"""Animates a `sim --record` directory into vcu.gif: relay pads, opmode polled over the terminal, 0x1D4 torque.
usage: make_gif.py <record dir> vcu.gif "tag"   (matplotlib, pillow)"""
import json, re, sys, io
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
rec = sys.argv[1]
rows = lambda f: (json.loads(l) for l in open(f"{rec}/{f}"))
PADS = {("gpioPortA", 8): "inv_out PA8", ("gpioPortC", 6): "prec_out PC6", ("gpioPortC", 7): "dcsw_out PC7"}
ev = {n: [(0, 0)] for n in PADS.values()}
for d in rows("gpio.jsonl"):
    n = PADS.get((d["port"], d["pin"]))
    if n: ev[n].append((d["t"], d["level"]))
tq = []
for d in rows("frame.jsonl"):
    if d.get("protocol") == "can" and d.get("direction") == "tx" and d["id"] == 0x1D4:
        b = bytes.fromhex(d["data"]); v = ((b[2] << 4) | (b[3] >> 4)) & 0xFFF
        tq.append((d["t"], (v - 4096 if v & 0x800 else v) / 2047 * 100))
names, op, cur = None, [], None
for d in rows("uart.jsonl"):
    if "→ term" not in d["label"]: continue
    s = d["text"].strip(); m = re.match(r"get ([\w,]+)", s)
    if m: names = m[1].split(","); cur = [d["t"]]; op.append(cur)
    elif names and re.fullmatch(r"-?\d+(\.\d+)?", s) and len(cur) <= len(names): cur.append(float(s))
op = [(r[0], r[1 + names.index("opmode")]) for r in op if len(r) == len(names) + 1]
end = 25.0; frames = []
for k in range(1, 41):
    tc = end * k / 40
    fig, ax = plt.subplots(3, 1, figsize=(7, 5), dpi=70, sharex=True)
    for i, (n, e) in enumerate(ev.items()):
        e2 = [x for x in e if x[0] <= tc]
        ax[0].step([t for t, _ in e2] + [tc], [v * .8 + 2 * (2 - i) for _, v in e2] + [e2[-1][1] * .8 + 2 * (2 - i)], where="post")
        ax[0].text(end + .2, 2 * (2 - i) + .3, n, fontsize=6)
    ax[0].set_yticks([]); ax[0].set_ylabel("relay outputs", fontsize=7)
    o = [x for x in op if x[0] <= tc]; ax[1].step([t for t, _ in o], [v for _, v in o], where="post", c="C3")
    ax[1].set_yticks(range(5)); ax[1].set_yticklabels(["OFF", "RUN", "PRECH", "PCHFAIL", "CHARGE"], fontsize=6); ax[1].set_ylim(-.3, 4.3); ax[1].set_ylabel("opmode (terminal)", fontsize=7)
    q = [x for x in tq if x[0] <= tc]; ax[2].plot([t for t, _ in q], [v for _, v in q], c="C2"); ax[2].set_ylim(-25, 5); ax[2].set_ylabel("0x1D4 torque, %", fontsize=7)
    ax[2].set_xlim(0, end); ax[2].set_xlabel("virtual time, s")
    ax[0].set_title(f"Stm32-vcu firmware on simulated F107, t={tc:.1f} s virtual, {sys.argv[3]}", fontsize=8)
    fig.tight_layout(); bf = io.BytesIO(); fig.savefig(bf, format="png"); plt.close(fig)
    frames.append(Image.open(bf).convert("RGB").quantize(colors=64, dither=Image.Dither.NONE))
frames[0].save(sys.argv[2], save_all=True, append_images=frames[1:], duration=[120] * 39 + [1500], loop=0, optimize=True)
