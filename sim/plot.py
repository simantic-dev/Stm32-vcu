"""Read a `sim --record` directory: relay/ignition pads (gpio.jsonl), CAN frames the VCU transmitted (frame.jsonl) and the polled
terminal values (uart.jsonl). Writes a PNG and prints the measured numbers."""
import json, re, sys, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rec, out = sys.argv[1], sys.argv[2]
rows = lambda f: (json.loads(l) for l in open(f"{rec}/{f}"))

# pads: (port, pin) -> name. Inputs are the scripted switches (io_peer.py), outputs are the VCU's.
PADS = {("gpioPortD", 6): "ignition (T15, scripted)", ("gpioPortD", 7): "start button (scripted)", ("gpioPortA", 15): "brake (scripted)",
        ("gpioPortA", 8): "inv_out PA8", ("gpioPortC", 6): "prec_out PC6", ("gpioPortC", 7): "dcsw_out PC7"}
ev = {n: [] for n in PADS.values()}
for d in rows("gpio.jsonl"):
    n = PADS.get((d["port"], d["pin"]))
    if n:
        ev[n].append((d["t"], d["level"]))
rise = lambda n: [t for t, v in ev[n] if v and t > 0.01]
fall = lambda n: [t for t, v in ev[n] if not v and t > 0.01]

# CAN frames transmitted by the VCU
tx = {}
for d in rows("frame.jsonl"):
    if d.get("protocol") == "can" and d.get("direction") == "tx":
        tx.setdefault(d["id"], []).append((d["t"], bytes.fromhex(d["data"])))
per = lambda i: st.median(b - a for (a, _), (b, _) in zip(tx[i], tx[i][1:])) * 1e3

def torque(b):
    v = ((b[2] << 4) | (b[3] >> 4)) & 0xFFF
    return v - 4096 if v & 0x800 else v
tq = [(t, torque(b) / 2047 * 100) for t, b in tx[0x1D4]]

# terminal polls: echo line "get a,b,c" then one value per line
names, polls, errors = None, [], []
for d in rows("uart.jsonl"):
    if "→ term" not in d["label"]:
        continue
    s = d["text"].strip()
    m = re.match(r"get ([\w,]+)", s)
    if m:
        names = m.group(1).split(","); cur = [d["t"]]; polls.append(cur)
    elif s.startswith("[") and "STOP" in s:
        errors.append((d["t"], s))
    elif names and re.fullmatch(r"-?\d+(\.\d+)?", s) and len(cur) <= len(names):
        cur.append(float(s))
polls = [r for r in polls if len(r) == len(names) + 1]
col = {n: [r[i + 1] for r in polls] for i, n in enumerate(names)}
tt = [r[0] for r in polls]

fig, ax = plt.subplots(4, 1, figsize=(11, 13), constrained_layout=True, sharex=True)
for i, (n, e) in enumerate(ev.items()):
    xs = [0] + [t for t, v in e] + [25]; ys = [0] + [v for t, v in e] + [e[-1][1] if e else 0]
    ax[0].step(xs, [y * 0.8 + 2 * (len(ev) - i) for y in ys], where="post", lw=1.2)
    ax[0].text(25.2, 2 * (len(ev) - i) + 0.3, n, fontsize=8, va="center")
ax[0].set(yticks=[], title="STM32 VCU firmware on a simulated STM32F107VC: switches in (scripted), relay outputs out (from the pad edges)")
ax[1].step(tt, col["opmode"], where="post", color="#d62728", label="opmode")
ax[1].set_yticks([0, 1, 2, 3, 4]); ax[1].set_yticklabels(["OFF", "RUN", "PRECHARGE", "PCHFAIL", "CHARGE"])
ax[1].set(title="state machine, polled over the serial terminal (USART3, `get`, every 250 ms)")
for t, s in errors:
    ax[1].annotate("`errors` at %.1f s: %s" % (t, s.split("- ")[-1]), (t, 3.5), fontsize=8, ha="right")
a2 = ax[2]
a2.plot([t for t, _ in tq], [v for _, v in tq], lw=1.2, color="#1f77b4", label="CAN 0x1D4 torque request (% of 2047)")
a2.set(xlabel='', ylabel="%", title="Leaf inverter CAN1: torque request sent every 10 ms in RUN (regen: lift-off at 2000 rpm, then brake)")
a2b = a2.twinx(); a2b.step(tt, col["speed"], where="post", color="#7f7f7f", label="speed from inverter 0x1DA (scripted, rpm)"); a2b.set_ylabel("rpm")
h = a2.get_legend_handles_labels(); h2 = a2b.get_legend_handles_labels(); a2.legend(h[0] + h2[0], h[1] + h2[1], loc="center left")
chg = [(t, ((b[0] << 8) | b[1]) / 10, ((b[2] << 8) | b[3]) / 10) for t, b in tx.get(0x1806E5F4, [])]
ax[3].step([c[0] for c in chg], [c[2] for c in chg], where="post", color="#2ca02c", label="CAN 0x1806E5F4 current command (A)")
ax[3].set(xlabel="virtual time (s)", ylabel="A", title="Elcon charger CAN2: current command from BMS charge limit (10 A) and Pwrspnt (1500 W)")
ax[3].legend(loc="upper left"); ax[3].set_xlim(0, 25)
fig.savefig(out, dpi=110)

pf = [t for t in rise('prec_out PC6')]
print(f"attempt 1 (no HV bus): start button {rise('start button (scripted)')[0]:.3f} s -> inv_out {rise('inv_out PA8')[0]:.4f} s, prec_out {pf[0]:.4f} s, prec_out released {fall('prec_out PC6')[0]:.4f} s ({fall('prec_out PC6')[0]-pf[0]:.2f} s closed) = precharge timeout")
print(f"attempt 2 (HV bus present): start button {rise('start button (scripted)')[1]:.3f} s -> inv_out {rise('inv_out PA8')[1]:.4f} s, dcsw_out {rise('dcsw_out PC7')[0]:.4f} s; prec_out closed again: {len(pf) > 1}")
print(f"charge: chargemodes set at 16.000 s -> inv_out {rise('inv_out PA8')[2]:.4f} s; opmode CHARGE reached: {4.0 in col['opmode']}")
print("opmode states seen over the terminal: " + ", ".join(str(int(x)) for x in sorted(set(col["opmode"]))) + "  (0 OFF, 1 RUN, 2 PRECHARGE, 3 PCHFAIL, 4 CHARGE)")
print("errors command: " + "; ".join(e for _, e in errors))
for i, name in ((0x11A, "0x11A gear/status"), (0x1D4, "0x1D4 torque"), (0x1DB, "0x1DB"), (0x1DC, "0x1DC"), (0x1F2, "0x1F2"), (0x50B, "0x50B"), (0x55B, "0x55B"), (0x59E, "0x59E"), (0x5BC, "0x5BC")):
    print(f"CAN1 TX {name}: {len(tx[i])} frames, median period {per(i):.2f} ms, first {tx[i][0][0]:.3f} s, last {tx[i][-1][0]:.3f} s")
lift = [(t, v) for t, v in tq if v < -1 and t < 12.5]
brk = [(t, v) for t, v in tq if 12.5 <= t <= 14.0]
print(f"regen on lift-off (speed 2000 rpm from 12.000 s, pedal at rest): {len(lift)} frames before the brake, torque {lift[0][1]:.2f} -> {lift[-1][1]:.2f} %, first {lift[0][0]:.3f} s")
print(f"regen with brake (PA15 high 12.500-14.000 s): torque {min(v for _, v in brk):.2f} % ({round(min(v for _, v in brk) * 2047 / 100)} raw)")
print(f"torque once speed is back to 0 (from 14.5 s): {set(round(v, 2) for t, v in tq if t > 14.5)} %, 0x1D4 frames outside regen: all zero before 12.0 s: {set(round(v, 2) for t, v in tq if t < 12.0)} %")
if chg:
    print(f"CAN2 TX 0x1806E5F4 (Elcon): {len(chg)} frames, median period {per(0x1806E5F4):.1f} ms, first {chg[0][0]:.3f} s, last {chg[-1][0]:.3f} s; command {chg[-1][1]:.1f} V, {chg[-1][2]:.1f} A")
print(f"CAN2 TX other ids (BMW E46 dash): " + ", ".join(f"0x{i:X} x{len(v)} @ {per(i):.1f} ms" for i, v in sorted(tx.items()) if i in (0x316, 0x329, 0x43B, 0x545)))
print(f"terminal: {len(polls)} polls; BMS_ChargeLim {col['BMS_ChargeLim'][-1]} A; udcsw {col['udcsw'][-1]} V")
