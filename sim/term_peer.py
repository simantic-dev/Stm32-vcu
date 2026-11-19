"""Serial terminal on USART3 (115200 8N1), scripted: configures the VCU at 0.2 s, polls POLL every POLL_MS, and switches
the Elcon charger on at CHARGE_ON / off at CHARGE_OFF. The firmware echoes the command and prints one value per line."""
POLL = "opmode,status,udc,udcsw,speed,dir,potnom,torque,BMS_ChargeLim,chgtyp"
POLL_MS = 250
# Inverter 1 = Leaf, Vehicle left at its default 0 = BMW E46, BMS_Mode 1 = SimpBMS, dirmode 4 = default forward (no fwd switch),
# potmin 50: the F103 ADC reads 0 here (no analog input in this sim build) and the firmware starts only with pot < potmin,
# so the pedal's resting calibration value is declared as 50 dig instead of measured.
# regenBrake -20: regen with the brake pad pressed (default -10, the same as lift-off regen regenmax), so the pad is visible in the torque.
SETUP = [(0.20, "set Inverter 1"), (0.24, "set BMS_Mode 1"), (0.26, "set dirmode 4"), (0.28, "set potmin 50"), (0.30, "set regenBrake -20")]
CHARGE_ON, CHARGE_OFF = 16.0, 20.5

class Peer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.n = 0
        self.todo = SETUP + [(CHARGE_ON, "set chargemodes 6"), (CHARGE_OFF, "set chargemodes 0"), (21.2, "errors")]
        ctx.schedule_periodic_ns(10_000_000)

    def on_timer(self):
        self.n += 1
        t = self.n * 0.010
        for at, cmd in self.todo:
            if abs(t - at) < 0.005:
                self.ctx.send((cmd + "\n").encode())
        if t >= 0.5 and self.n % (POLL_MS // 10) == 0:
            self.ctx.send(("get " + POLL + "\n").encode())

    def on_byte(self, b):
        pass
