"""Elcon/TC AC charger on CAN2 (extended ids), scripted. Every 1 s it reports 0x18FF50E5: output volts x0.1, amps x0.1, status.
It reports the current the VCU last commanded in 0x1806E5F4 (bytes 2-3, x0.1 A) and the HV volts it was told to hold, once commanded; zero before."""
class Node:
    def __init__(self, ctx):
        self.ctx = ctx
        self.n = 0
        self.volts = self.amps = 0
        ctx.schedule_periodic(1_000_000)

    def on_timer(self):
        v, a = self.volts, self.amps
        self.ctx.send(0x18FF50E5, bytes([v >> 8, v & 255, a >> 8, a & 255, 0, 0, 0, 0]))

    def on_frame(self, f):
        if f["id"] == 0x1806E5F4:
            d = bytes(f["data"])
            self.volts = (d[0] << 8) | d[1]
            self.amps = (d[2] << 8) | d[3]
