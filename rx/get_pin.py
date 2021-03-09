# get_pin.py Return a Pin instance for RX

# Author: Peter Hinch
# Copyright Peter Hinch 2020 Released under the MIT license

from machine import Pin, freq
from sys import platform

def pin():
    # Define pin according to platform
    if platform == 'pyboard':
        pin = Pin('X3', Pin.IN)
    elif platform == 'esp8266':
        raise OSError('Receiver does not support ESP8266')
        #freq(160000000)
        #pin = Pin(13, Pin.IN)
    elif platform == 'esp32' or platform == 'esp32_LoBo':
        pin = Pin(27, Pin.IN)
    elif platform == 'rp2':  # Raspberry Pi Pico
        pin = Pin(17, Pin.IN)
    return pin
