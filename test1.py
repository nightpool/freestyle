
import pyaudio, numpy as np
from collections import namedtuple

CHUNK = 256
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
THRESHOLD = 1.5e7

Chunk = namedtuple('Chunk', 'data time')
Clap = namedtuple('Clap', 'time duration magnitude',)

class MicrophoneFeed(object):
    def __init__(self):
        self.enabled = True
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                                  input=True, frames_per_buffer=CHUNK)
        self.t = 0.0

    def __iter__(self):
        while self.enabled:
            data = self.stream.read(CHUNK)
            chunk = np.fromstring(data, 'int16')
            t = self.t
            self.t += float(CHUNK) / RATE
            yield Chunk(chunk, t)

    def close(self):
        self.stream.stop_stream()
        self.enabled = False

    def open(self):
        self.stream.start_stream()
        self.enabled = True

class VerboseFeed(object):
    def __init__(self, feed):
        self.feed = feed

    def __iter__(self):
        for c in self.feed:
            # print('*' * (abs(c.data).sum() // 250000))
            yield c

SLOW = 0.050
FAST = 0.25

class EdgeDetector():
    "Call a sufficiently noisy event a clap."

    def __init__(self, feed, threshold):
        self.slow = 0
        self.fast = 0
        self.threshold = threshold
        self.feed = feed

        self.current_clap = None
        self.current_mag = 0
        self.empty = 0

    def __iter__(self):
        for c in self.feed:
            edge = self.step(c)

            if edge > self.threshold:
                if self.current_clap:
                    self.current_mag = max(edge, self.current_mag)
                else:
                    self.current_clap = c.time
                    self.current_mag = edge
            elif self.current_clap:
                duration = c.time - self.current_clap
                clap = Clap(self.current_clap, duration, self.current_mag)
                self.current_clap = None
                self.current_mag = 0
                self.empty = 0
                yield ('clap', clap)
            else:
                self.empty += 1
                if self.empty > 200:
                    self.empty = 0
                    yield ('break', None)

    def step(self, chunk):
        val = abs(chunk.data).sum()
        self.slow = val * SLOW + self.slow * (1-SLOW)
        self.fast = val * FAST + self.fast * (1-FAST)
        edge = self.fast - self.slow
        s = ('*' * (edge // 200000))
        if s: print s
        return edge

if __name__ == '__main__':
    mic = MicrophoneFeed()
    detector = EdgeDetector(VerboseFeed(mic), 500000)

    tempo = []
    import time
    while True:
        for t, clap in detector:
            if t == 'clap':
                print 'clap'
                tempo.append(clap)
            if len(tempo) >= 4:
                break
        for i, c in enumerate(tempo):
            if i > 0:
                print c.time - tempo[i-1].time
        tempo = []
        mic.close()
        time.sleep(2)
        print "back up!"
        mic.open()

    while True:
        for clap in detector:
            print('=== CLAP === ', clap)
            # thing, value = clap
            # if thing == 'break' and claps
