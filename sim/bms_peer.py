"""SimpBMS-style battery management on CAN2, scripted (what the VCU's simpbms driver decodes), every 100 ms:
0x373 min/max cell mV + min/max temp (K), 0x351 charge limits (0.1 A), 0x355 SOC (%), 0x356 pack voltage (0.01 V) and current (0.1 A).
Static values: a healthy 96s pack at 3.75 V/cell, 25 C, 10 A charge limit. No pack model."""
import struct
class Node:
    def __init__(self, ctx):
        self.ctx = ctx
        ctx.schedule_periodic(100_000)

    def on_timer(self):
        s = self.ctx.send
        s(0x373, struct.pack("<HHHH", 3700, 3800, 298, 300))
        s(0x351, struct.pack("<HHHH", 4100, 100, 100, 3000))
        s(0x355, struct.pack("<HHHH", 80, 100, 0, 0))
        s(0x356, struct.pack("<HhHH", 36000, 0, 250, 0))

    def on_frame(self, f):
        pass
