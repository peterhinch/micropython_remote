# rx __init__.py Capture utility for 433MHz remote control.

# Author: Peter Hinch
# Copyright Peter Hinch 2020 Released under the MIT license

from array import array
from utime import ticks_us, ticks_diff
import ujson
import gc
from math import sqrt

class RX():

    def __init__(self, pin, nedges=800):  # Typically ~15 frames
        self._pin = pin
        self._nedges = nedges
        self._data = {}
        gc.collect()
        # Store arrival times of edges in μs
        self._times = array('I',  (0 for _ in range(nedges)))

    def __getitem__(self, key):  # View list of pulse lengths: print(receiver['on'])
        if key in self._data:
            return self._data[key]
        print('Key "{}" does not exist'.format(key))

    def __delitem__(self, key):  # Key deletion: del receiver['on']
        del self._data[key]

    def keys(self):
        return self._data.keys()

    def show(self, key):
        res = self[key]
        if res is not None:
            for x, t in enumerate(res):
                print('{:3d} {:6d}'.format(x, t))

    # Attempt to achieve better precision by averaging several frames
    def process(self, diffs):
        ermsg = 'FAIL: too few valid frames.'
        gap = round(max(diffs) * 0.8)  # Allow for tolerance
        # Discard data prior to and including 1st gap
        while diffs[0] < gap:
            diffs.pop(0)
        diffs.pop(0)

        # diffs starts with 1st pulse
        res = []  # list of frames. Each entry ends with gap.
        while True:
            lst = []
            try:
                while diffs[0] < gap:
                    lst.append(diffs.pop(0))
                lst.append(diffs.pop(0))  # Add the gap
            except IndexError:
                break  # all done
            res.append(lst)

        # List of frames. May have some with invalid lengths.
        lengths = [len(x) for x in res]
        if len(lengths) < 5:
            print(ermsg)  # Too few frames
            return
        #print('Lengths', lengths)
        d = {x: 0 for x in set(lengths)}
        for l in lengths:
            d[l] += 1
        count = max(d.values())  # Find most common frame length
        for length in d.keys():
            if d[length] == count:
                break
        old = len(res)
        print('Frame length = {} No. of frames = {}'.format(length, old))
        res = [r for r in res if len(r) == length]
        # All frames have same length
        cnt = len(res)
        if cnt != old:
            print('Deleted {} frames of wrong length'.format(old - cnt))
        if cnt < 5:
            print(ermsg)
        else:
            print('Averaging {} frames'.format(cnt))
            m = [round(sum(x)/cnt) for x in zip(*res)]  # Mean values
            s = [sqrt(sum([(y - m[i])**2 for y in x])) for i, x in enumerate(zip(*res))]  # Standard deviations
            print('Capture quality {:5.1f} (perfect = 0)'.format(sum(s)/len(s)))
            return [round(x) for x in m]

    def __call__(self, key):
        print('Awaiting radio data')
        nedges = self._nedges
        x = 0
        p = self._pin
        # ** Time critical **
        while x < nedges:
            v = p()
            while v == p():
                pass
            self._times[x] = ticks_us()
            x += 1
        # ** End of time critical **
        diffs = []
        for x in range(nedges - 2):
            diffs.append(ticks_diff(self._times[x + 1], self._times[x]))
        # Perform error checking and averaging.
        res = self.process(diffs)
        if res is None:
            print('Capture failed: please try again.')
        else:
            self._data[key] = res
            print('Key "{}" stored.'.format(key))

    def load(self, fname):  # Import file (will overwrite existing keys)
        try:
            with open(fname, 'r') as f:
                self._data.update(ujson.load(f))
        except OSError:
            print("Can't open '{}' for reading.".format(fname))

    def save(self, fname):
        try:
            with open(fname, 'w') as f:
                ujson.dump(self._data, f)
        except OSError:
            print("Can't open '{}' for writing.".format(fname))
        else:
            print('Data saved in file {}'.format(fname))
