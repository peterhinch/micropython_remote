# __init__.py Nonblocking 433MHz transmitter
# Runs on Pyboard D, Pyboard 1.x, Pyboard Lite, ESP32 and Raspberry Pi Pico

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2020-2021 Peter Hinch

from sys import platform
ESP32 = platform == 'esp32'  # Loboris not supported owing to RMT
RP2 = platform == 'rp2'
if ESP32:
    from esp32 import RMT
elif RP2:
    from .rp2_rmt import RP2_RMT
else:
    from pyb import Timer

from machine import Pin
from array import array
from time import ticks_us, ticks_diff, sleep_us
import gc
import ujson

# import micropython
# micropython.alloc_emergency_exception_buf(100)
STOP = const(0)

# TX class. Physical transmission occurs in an ISR context controlled by timer 5.
class TX:
    _active_high = True

    @classmethod
    def active_low(cls):
        if ESP32:
            raise ValueError('Cannot set active low on ESP32')
        cls._active_high = False

    def __init__(self, pin, fname, reps=5):
        self._pin = pin
        self._reps = reps
        with open(fname, 'r') as f:
            self._data = ujson.load(f)
        # Time to wait between nonblocking transmissions. A conservative value in ms.
        self._latency = (reps + 2) * max((sum(x) for x in self._data.values())) // 1000
        gc.collect()
        if ESP32:
            self._rmt = RMT(0, pin=pin, clock_div=80)  # 1μs resolution
        elif RP2:  # PIO-based RMT-like device
            self._rmt = RP2_RMT(pin_pulse=pin)  # 1μs resolution
            # Array size: length of longest entry + 1 for STOP
            asize = max([len(x) for x in self._data.values()]) + 1
            self._arr = array('H', (0 for _ in range(asize)))  # on/off times (μs)
        else:  # Pyboard
            self._tim = Timer(5)  # Timer 5 controls carrier on/off times
            self._tcb = self._cb  # Pre-allocate
            asize = reps * max([len(x) for x in self._data.values()]) + 1  # Array size
            self._arr = array('H', (0 for _ in range(asize)))  # on/off times (μs)
            self._aptr = 0  # Index into array

    def _cb(self, t):  # T5 callback, generate a carrier mark or space
        t.deinit()
        p = self._aptr
        v = self._arr[p]
        if v == STOP:
            self._pin(self._active_high ^ 1)
            return
        self._pin(p & 1 ^ self._active_high)
        self._tim.init(prescaler=84, period=v, callback=self._tcb)
        self._aptr += 1

    def __getitem__(self, key):
        return self._data[key]

    def keys(self):
        return self._data.keys()

    def show(self, key):
        res = self[key]
        if res is not None:
            for x, t in enumerate(res):
                print('{:3d} {:6d}'.format(x, t))

    def latency(self):
        return self._latency

    # Nonblocking transmit
    def __call__(self, key):
        gc.collect()
        lst = self[key]
        if lst is not None:
            if ESP32:
                # TODO use RMT.loop() cancelled by a soft timer to do reps.
                # This would save RAM. RMT.loop() is now fixed. I remain
                # unconvinced because of the huge latency of soft timers on
                # boards with SPIRAM. It would save ram if a half-word array
                # could be passed. But it can't (as of 9th March 2021).
                # Prior to July 2021 start = 1 was required. Now this breaks
                # and 1 is the default.
                self._rmt.write_pulses(lst * self._reps)  #, start = 1)
            elif RP2:
                for x, t in enumerate(lst):
                    self._arr[x] = t
                self._arr[x + 1] = STOP
                self._rmt.send(self._arr, self._reps)
            else:
                x = 0
                for _ in range(self._reps):
                    for t in lst:
                        self._arr[x] = t
                        x += 1
                self._arr[x] = STOP
                self._aptr = 0  # Reset pointer
                self._cb(self._tim)  # Initiate physical transmission.

    # Blocking transmit: proved necessary on Pyboard Lite
    @micropython.native
    def send(self, key):
        gc.collect()
        pin = self._pin
        q = self._active_high ^ 1  # Pin inactive state
        lst = self[key]
        if lst is not None:
            for _ in range(self._reps):
                pin(q)
                for t in lst:
                    pin(pin() ^ 1)
                    sleep_us(t)
        pin(q)
