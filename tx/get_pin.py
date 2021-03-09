# get_pin.py Return a Pin instance for TX

# Author: Peter Hinch
# Copyright Peter Hinch 2020 Released under the MIT license

from machine import Pin
from sys import platform

def pin(state=0):
    # Define pin according to platform
    if platform == 'pyboard':
        pin = Pin('X3', Pin.OUT)
    elif platform == 'esp32':
        pin = Pin(23, Pin.OUT)
    elif platform == 'rp2':  # Raspberry Pi Pico
        pin = Pin(16, Pin.OUT)
    elif platform == 'esp8266':
        raise OSError('Transmitter does not support ESP8266')
    elif platform == 'esp32_LoBo':
        raise OSError('Transmitter does not support Loboris port')
    else:
        raise OSError('Unsupported platform', platform)
    pin(state)
    return pin
