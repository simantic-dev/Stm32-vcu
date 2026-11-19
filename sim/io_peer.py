"""Scripted driver inputs on digital pads (not a plant: fixed switch positions at fixed times).
Outputs, in order: PD6 ignition (T15), PD7 start button, PA15 brake switch, PD5 and PD4 (external HV request, 12 V input: tied low),
PE3-PE5 (gear/aux inputs, active low: pulled up on the board, so tied high). Without the last five the pads float on the bare chip,
and the firmware's default pin map (HVReqFunc 2 = the same function as PB3InFunc, i.e. PE5, inverted) reads a permanent HV request."""
EVENTS = [(0, 0, 0), (0, 1, 0), (0, 2, 0), (0, 3, 0), (0, 4, 0), (0, 5, 1), (0, 6, 1), (0, 7, 1),
          (1.0, 0, 1), (1.2, 1, 1), (1.5, 1, 0),      # attempt 1 (no HV bus): ignition on, start button
          (8.5, 0, 0),                                 # ignition off
          (9.5, 0, 1), (9.7, 1, 1), (10.0, 1, 0),     # attempt 2 (HV bus present)
          (12.5, 2, 1), (14.0, 2, 0),                  # brake pedal pressed 1.5 s
          (15.0, 0, 0)]                                # ignition off

class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self.todo = sorted(EVENTS)
        self._arm()

    def _arm(self):
        if self.todo:
            self.ctx.schedule_oneshot_ns(max(1, int(self.todo[0][0] * 1e9) - self.ctx.now_ns))

    def on_timer(self):
        while self.todo and int(self.todo[0][0] * 1e9) <= self.ctx.now_ns:
            _, i, lvl = self.todo.pop(0)
            self.ctx.gpio(i).set(bool(lvl))
        self._arm()

    def on_gpio(self, line, level):
        pass
