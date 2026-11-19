"""Nissan Leaf inverter on CAN1 (500 kbit/s), scripted. Sends what the VCU's Leaf driver decodes:
0x1DA every 10 ms (DC voltage = byte0 x 2 V, motor speed = 15 bit at bytes 4-5) and 0x55A every 100 ms (temperatures, deg F).
Scripted stimulus, not a model: DC link voltage is 0 until HV_ON_S (second attempt) then 360 V; speed is a time table."""
HV_ON_S = 9.5                                   # attempt 1 has no HV bus -> precharge must time out
SPEED = [(0, 0), (12.0, 2000), (14.0, 0)]       # rpm: (seconds, value)

class Node:
    def __init__(self, ctx):
        self.ctx = ctx
        self.n = 0
        ctx.schedule_periodic(10_000)

    def on_timer(self):
        self.n += 1
        t = self.n * 0.010
        rpm = [v for at, v in SPEED if t >= at][-1]
        volts = 360 if t >= HV_ON_S else 0
        d = bytearray(8)
        d[0] = volts // 2
        d[4] = (rpm >> 7) & 0x7F
        d[5] = (rpm & 0x7F) << 1
        self.ctx.send(0x1DA, bytes(d))
        if self.n % 10 == 0:
            self.ctx.send(0x55A, bytes([0, 104, 104, 0, 0, 0, 0, 0]))   # 40 C motor, 40 C inverter

    def on_frame(self, f):
        pass
